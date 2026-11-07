---
name: fastapi
description: Use when building or changing a FastAPI service (API-only backends, middleware to external services, embeddable widget backends) in an OEES project.
---

# FastAPI services

This is how we build a FastAPI service: Python 3.13, uv, FastAPI, SQLAlchemy 2 async on Postgres 16,
Alembic, Pydantic settings, httpx for outbound calls, structlog JSON logs, one container, deployed
to DigitalOcean App Platform. Copy the templates listed at the end; they are tested and pass
`make check` as copied.

## Layout

The application package is `app/` at the project root (no `src/`), organised by domain. Files that
change together live together:

```
app/
  main.py                create_app() factory and lifespan
  api.py                 /api/v1 router; includes every domain router
  models.py              imports every domain's models so Alembic sees them
  settings/              base, local, test, production
  core/                  shared plumbing: db, errors, health, http, logging, pagination, request_id
  <domain>/
    router.py            HTTP only: parse input, call the service, shape the response
    schemas.py           Pydantic request and response models
    service.py           business rules; raises DomainError subclasses; commits
    repository.py        SQLAlchemy queries; no business rules, no commits
    models.py            ORM classes with typed Mapped[...] columns
migrations/              Alembic, async env.py
tests/                   mirrors app/ (tests/core/test_health.py tests app/core/health.py)
```

- Routers never touch the session beyond passing it on, and never catch domain errors.
- Services own the transaction: they call `await session.commit()`. The session dependency
  (`SessionDep`) opens one session per request and closing it rolls back anything uncommitted.
- Models subclass `app.core.db.Base`, whose `MetaData` carries a naming convention, so every
  constraint has a deterministic name Alembic can drop later.
- A new domain is registered twice: its router in `app/api.py`, its models in `app/models.py`.
- Endpoints are `async def` and the engine is async (asyncpg) because our services are I/O bound:
  they wait on Postgres and other HTTP services.
- Every endpoint lives under `/api/v1/`; list endpoints take `PageQuery` and return `Page[Schema]`
  (`count`, `next`, `previous`, `results`; `page` and `page_size`, default 50, max 200). The
  repository calls `fetch_page(session, statement, params)` with an ordered statement.
- Outbound HTTP goes through the one shared `httpx.AsyncClient` (`HttpClientDep`), created in the
  lifespan. It has explicit timeouts, connect retries in the transport, and `RetryTransport`, our
  small tested wrapper (no tenacity), which retries idempotent methods on 429 and 5xx with
  exponential backoff, jitter and `Retry-After`. It sends the current request id as `X-Request-ID`.
  Never create a client per call. Wrap each external service in a small client class in its domain
  that takes the shared client and raises `ExternalServiceError` on unusable answers.

Deviate when the project context says so, e.g. a CPU-bound or sync-only service (bill-e's PDF and
local-LLM work) uses the sync engine with psycopg and plain `def` endpoints.

## Settings

`app/settings/` holds `base.py` (every field, typed, with defaults), `local.py`, `test.py` and
`production.py`. `APP_ENV` selects the class; there is no default, so a missing or misspelt value
fails at startup. Code reads settings only through the cached `get_settings()`, and the app keeps
the instance on `app.state.settings`.

- Secrets are `SecretStr` (the database URL included) so they never appear in a repr or a log.
- `local` reads `.env`; `production` reads only real environment variables; `test` reads neither
  `.env` nor `DATABASE_URL`, only `TEST_DATABASE_URL`, so tests never touch the dev database.
- `async_database_url()` accepts the `postgresql://...?sslmode=require` URL App Platform injects
  and turns it into the asyncpg form.
- Every variable the settings read is listed in `.env.example` with a placeholder value.
- API docs are served at `/api/v1/docs` except in production (`docs_enabled = False`).

Deviate when the project context says so, e.g. a project with a staging environment adds
`staging.py` and registers it in `SETTINGS_BY_ENV`.

## Logging

structlog renders one JSON object per line to stdout; standard-library loggers (uvicorn, SQLAlchemy,
Alembic, httpx) go through the same formatter, so the whole process speaks one format.

- `RequestIdMiddleware` is pure ASGI. It takes `X-Request-ID` from the request when it is safe
  (`[A-Za-z0-9._-]{1,128}`), otherwise generates a uuid4 hex, binds it with structlog contextvars,
  and echoes it in the response header. Every log line in the request carries `request_id`.
- It writes the access line: event `request` with `method`, `path`, `status`, `duration_ms`.
  Successful `/healthz` and `/readyz` calls log at DEBUG to keep probe noise out. uvicorn's own
  access log is off (`--no-access-log`).
- `redact_sensitive` replaces values of keys containing `password`, `secret`, `token`,
  `authorization`, `cookie`, `api_key`, `database_url`, `dsn`, `email`, `phone`, `iban` (and the
  exact keys `dni`, `nie`, `nif`) at any depth. Extend the list in `app/core/logging.py` when a
  domain adds new personal data; never log a whole request body.
- Event names are snake_case (`order_created`, `http_retry`) with context as keyword fields, never
  interpolated into the message.

## Errors

Every non-2xx JSON response uses the envelope
`{"error": {"code", "message", "details", "request_id"}}`; `app/core/errors.py` registers the
handlers in `create_app()`.

- Services raise `DomainError` subclasses. Each subclass sets `code` and `status_code` once:
  `NotFoundError` (404), `ConflictError` (409), `PermissionDeniedError` (403),
  `ExternalServiceError` (502). Add a subclass per meaning, not per call site.
- `HTTPException` (Starlette's, so unknown routes and wrong methods are covered) keeps its status,
  message and headers; the code comes from the status (`not_found`, `method_not_allowed`...).
- `RequestValidationError` returns 422 `validation_error` with details `{"field": ["message"]}`.
- Anything else returns 500 `internal_error` with a fixed message and is logged at ERROR with the
  stack trace. Never put exception text in a response.

## Tests

Tests live in the top-level `tests/`, mirroring `app/`: `app/core/health.py` is tested in
`tests/core/test_health.py`, `app/billing/service.py` in `tests/billing/test_service.py`. pytest with
pytest-asyncio in auto mode; `filterwarnings = error`.

- `tests/conftest.py` forces `APP_ENV=test`, applies the real migrations once per session, and runs
  every test in a transaction rolled back at the end (`join_transaction_mode="create_savepoint"`),
  so services can commit and tests stay isolated. Tests run against real Postgres, not SQLite.
- The `client` fixture is an `httpx.AsyncClient` on `ASGITransport` with the lifespan running.
- No test touches the network: outbound calls use `httpx.MockTransport` passed to
  `build_http_client(..., transport=...)`, or a dependency override of `get_http_client`.
- Mark tests over a second or so with `@pytest.mark.slow`; `make check-fast` skips them.
- Coverage floor 80% over `app/`, branch coverage on, greenlet concurrency so async SQLAlchemy
  code is measured.

## Makefile targets

`make check` is the gate CI runs: ruff lint, ruff format check, mypy strict (pydantic plugin),
pytest with coverage, `alembic upgrade head` plus `alembic check` on the test database, and
pip-audit on the exported lockfile. `make check-fast` runs lint, format check, mypy and the tests
not marked slow with `-x`; narrow it with `TESTS=tests/<domain>`. Also: `install`, `format`, `test`,
`run` (reload, against `docker compose up -d db`), `migrate`, and
`migration MESSAGE="..."` (autogenerate; the post-write hooks format the file).

In a container: `docker compose run --rm dev make check`.

Migrations follow the `migrations` rule. Here that means: autogenerate, then read and fix the
revision; write a real `downgrade()`; keep every revision backwards compatible with the code that
is running; ship it in a deploy before the code that needs it. The App Platform `PRE_DEPLOY` job
runs `alembic upgrade head` before the new code starts, and `alembic check` in `make check` fails
when models and migrations disagree.

## Container

One multi-stage `Dockerfile`: `builder` copies uv from its pinned image and installs the locked
production dependencies into `/app/.venv` (dependency layer before source, uv cache mount); `dev`
adds dev tools and make for `docker compose run --rm dev ...`; `runtime`, the last and default
stage, is `python:3.13.x-slim-bookworm` pinned by tag and digest, runs as uid 10001, and copies only
the venv, `app/`, `migrations/` and `alembic.ini`.

- `CMD` is exec form: `uvicorn app.main:create_app --factory`, workers from `WEB_CONCURRENCY`,
  `--log-config app/core/uvicorn_logging.json` so the worker supervisor also logs JSON,
  proxy headers trusted so `next`/`previous` links are `https` behind the platform router.
- `HEALTHCHECK` calls `/healthz` with the Python stdlib (slim has no curl).
- `/healthz` checks nothing but the process; `/readyz` runs `SELECT 1` with a 2 s timeout and
  returns 503 `{"status": "unavailable", "checks": {...}}` when the database does not answer.
- `compose.yml` is local only: `db` (Postgres 16, creates `app_test` on first start), `app` (the
  runtime image) and `dev` (profile `tools`). Copy `.env.example` to `.env` first.

## Deploy path

Pull request: `ci` runs `check` (Postgres service, `make check`), `secrets` (the pinned gitleaks
CLI image over the PR's commits; full history on push) and `image` (docker build, no push). Merge
to main: `ci` runs again; when it succeeds, `deploy` (a `workflow_run` of `ci` on main,
`environment: production`, one deploy at a time) applies `.do/app.yaml` with
`digitalocean/app_action`. App Platform builds the Dockerfile, runs the `migrate` `PRE_DEPLOY` job
(`alembic upgrade head`), then rolls out the `web` service, gated on `/healthz`. `deploy_on_push`
is off: CI is the only way in.

- App Platform builds the tip of main, so `deploy` first checks the commit `ci` tested is still the
  tip and skips with a notice when it is not; the newer commit's run deploys instead.
- Secrets live in the GitHub `production` environment. The deploy job passes each one as `env:`,
  the action substitutes it into `value: ${NAME}` (`type: SECRET`) in the spec, and App Platform
  stores it encrypted. A guard step fails the deploy if a `${NAME}` is unset, because an unset
  name is substituted as empty. Bindables such as `${db.DATABASE_URL}` (the managed cluster, bound
  into both components) pass through untouched.
- Every action and image is pinned to a commit SHA or digest with the tag beside it; bump both
  together.

## Templates

| Concern | Copy from `templates/` | Edit after copying |
|---|---|---|
| Dependencies, ruff, mypy, pytest, coverage | `pyproject.toml` | `name` (marked `# EDIT`), then `uv lock` |
| Quality gate and dev commands | `Makefile` | nothing |
| App factory, lifespan, routers | `app/main.py`, `app/api.py`, `app/models.py`, `app/__init__.py` | nothing; add domains as they appear |
| Settings | `app/settings/*.py` | nothing; add fields as needed |
| Shared core | `app/core/*.py`, `app/core/uvicorn_logging.json` | nothing |
| Migrations | `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/.gitkeep` | nothing |
| Tests for the core | `tests/conftest.py`, `tests/**/__init__.py`, `tests/test_main.py`, `tests/core/*.py`, `tests/settings/*.py` | nothing |
| Container | `Dockerfile`, `.dockerignore` | nothing |
| Local stack | `compose.yml`, `.env.example` | nothing |
| CI | `.github/workflows/ci.yml` | nothing |
| Deploy | `.github/workflows/deploy.yml` | nothing; create the `production` environment with `DIGITALOCEAN_ACCESS_TOKEN`; add an `env:` line per app secret |
| App Platform spec | `.do/app.yaml` | the `# EDIT:` lines: app name, region, GitHub repo, database cluster |
