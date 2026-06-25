# Contributing to OEES code

This is the master guide for contributing to **Octopus Energy España / Octopus
Energy Services (OEES / OES)** repositories. It is written for **AI coding
agents** first (Claude Code, Cursor) and humans second. If you are an agent
starting a session on any OEES repo, read this, then read that repo's own
`CLAUDE.md` / `README.md` — the repo always wins where they differ.

> **Why this exists.** We build energy software that customers and internal
> teams depend on. Our job is to make energy *fair, clean, and simple*, backed
> by outrageously good service. Code quality, safety, and transparency are how
> we keep that promise. Move fast, but never at the customer's expense.

---

## 0. Golden rules (read these first)

1. **Never write, delete, or perform an externally-visible action without
   explicit permission from the human in the current interaction.** This
   covers: pushing to a remote, deleting branches/files/DB rows, opening,
   closing, commenting on, or merging PRs/issues, sending messages (Slack,
   email), and editing `.env`, `docker-compose.prod.yml`, or any secret.
   Permission is **per specific action** — "yes, open the PR" does **not**
   authorise a later `git push --force`.
2. **Never merge PRs yourself.** A human reviews and merges from the GitHub UI.
3. **Never force-push to `main`/`master`.** Never use `--no-verify` to skip
   hooks — if a hook fails, fix the cause.
4. **Spec first for new features** (see §4). Bug fixes and minor refactors can
   go straight to a PR.
5. **Tests ship with the change** (see §5). Write the failing test first.
6. **The customer is the point.** When a trade-off is unclear, choose the
   option that gives the customer the best, safest, most transparent outcome.

---

## 1. The shared tooling: the `agents` repo

All OEES repos share one set of rules, slash commands, and skills, maintained in
the `agents` repo and installed into each project's `.claude/` and `.cursor/`
directories.

**Install / update tooling in a repo** (run from the repo root):

```bash
curl -fsSL https://raw.githubusercontent.com/oees/agents/main/scripts/bootstrap.sh | bash
git add .claude/ .cursor/ && git commit -m "chore: sync Claude Code and Cursor tooling"
```

Once committed, every engineer and agent on that repo inherits the same rules
automatically.

### Always-on rules

These are loaded into every agent session from the repo's `.claude/rules/`:

| Rule | Enforces |
|---|---|
| `tdd` | Failing test before behavioural change; red → green → refactor; tests in the same commit. |
| `code-quality` | Lint, format, type-check, test, and dependency-scan before merge. No merging known-failing checks. |
| `observability` | Structured logs with correlation IDs; never swallow exceptions silently. |
| `no-inline-imports` | Imports at module top, except documented circular-dependency cases. |
| `standards` | Frontend/backend/deploy/API conventions (see §3). |
| `git` | Rebase-always, no merge commits on `main`, no squashing, never force-push `main`. |
| `secrets` | No credentials in version control; env vars + secret managers; `gitleaks` in CI. |
| `migrations` | Backwards-compatible, reversible schema changes; migration ships before the code that needs it. |

### Slash commands

| Command | What it does |
|---|---|
| `/plan` | Full implementation plan from a spec, with TDD tasks and exact file paths. |
| `/test` | Write well-structured tests following TDD (mocking discipline, naming, coverage). |
| `/commit` | Well-formed atomic commit following team standards. |
| `/code-review` | Strict maintainability review (abstraction quality, file size, spaghetti growth). |
| `/pr-tidy` | Prepare a PR for review — clean history, rewrite description, add reviewer guidance. |
| `/shipped` | Summary of what you've committed across all local repos in a time period. |

Some repos add their own (e.g. OctoHub has `/create-pr` and `/sync-github`).
Prefer a repo's own PR/sync skills when present.

---

## 2. The repositories at a glance

| Repo | What it is | Stack |
|---|---|---|
| `octosentinel` | Multi-vendor energy-device monitoring platform (3,000+ plants, scaling to 50k+) | Django 5 + DRF, Celery, RabbitMQ, Redis, TimescaleDB/PostgreSQL 15, MQTT (Mosquitto), React 18 + Vite |
| `octohub` | B2B multi-tenant platform for selling/installing energy products (Partners + Vendors) | Django 5 + DRF, Celery, Redis 7, PostgreSQL 16, React 19 + TS + Vite + Tailwind + TanStack Query |
| `franklin` | Web app for OEES ambassadors to create energy accounts in Kraken | Django 6, Bootstrap 5 + vanilla JS, PostgreSQL, Kraken GraphQL API |
| `hermes` | Middleware to external services (Zoho CRM, etc.) — OAuth, retries, webhooks | FastAPI, SQLAlchemy 2.0, Celery, HTTPX, PostgreSQL |
| `bill-e` | Microservice: PDF electricity bill → plain-language explanation via local LLM | FastAPI, `uv`, pytest/hypothesis |
| `consumer-site-embeds` | Embeddable widgets (e.g. World Cup vote) | FastAPI, async SQLAlchemy + asyncpg, Alembic, Docker, DigitalOcean App Platform |
| `octopanel` | Internal panel (brand/design assets) | — |
| `vercel-deployer` | Internal app to publish pre-built static sites to Vercel without git | Next.js, TypeScript |

**Patterns you'll see repeatedly:** Django + DRF or FastAPI on the backend;
Celery + Redis/RabbitMQ for async work; PostgreSQL (TimescaleDB for telemetry);
React + TypeScript + Vite + TanStack Query on the frontend; everything runs in
**Docker**; deploys target **DigitalOcean App Platform** or **Vercel**.

---

## 3. Architecture conventions

- **Backend owns the truth.** Business rules, validation, authorization,
  persistence, and computed outcomes (KPIs, billing logic) live in backend
  services/domain apps — **never** duplicated in clients. Cosmetic derivation on
  the client is fine; authoritative rules are not.
- **Organise by domain, not by technical layer.** Files that change together
  live together. Keep tests in per-app `tests/` directories. Split Django
  settings by environment (`base` / `development` / `test` / `production`).
- **Frontend** handles UI, state orchestration, and API calls only. Strong
  static typing, schema validation at boundaries, a server-state cache
  (TanStack Query) with explicit invalidation — not `useState` for server data.
- **API design**: version under `/api/<version>/`, consistent error envelopes
  with correct HTTP status codes, paginate every list endpoint, typed schema
  validation, token-based auth with secure refresh, auto-generated docs.
- **Multi-tenancy** (where it applies, e.g. octosentinel/octohub): every
  governance row carries a `tenant_id`; enforce tenant scoping at the queryset
  level in every ViewSet.

---

## 4. Workflow: spec → plan → implement → PR

1. **New feature → write a spec first.** A self-contained doc (typically
   `docs/specs/<feature>.md`) with a **Vision** section (problem, goal, actors,
   out-of-scope) and a **Design** section (decisions, API/contract, changes per
   layer, risks, tests, open items). A human reviews and approves it **before**
   you implement. Bug fixes and minor refactors skip the spec.
2. **Plan it.** Use `/plan` to turn the spec into TDD tasks with exact file
   paths.
3. **Implement in small, reviewable PRs**, each with human approval. One logical
   change per commit.
4. **Open the PR** with the repo's PR skill (`/create-pr`) or `/pr-tidy`, using
   the Octopus PR template. A human merges from the GitHub UI.

---

## 5. Quality gates (non-negotiable before merge)

Run the **same checks locally and in CI**. Prefer a single command (`make check`
/ `npm run check` / the repo's `doctor.sh`) that runs lint + format + types +
tests with coverage.

- **Lint & format** — Python: `ruff check` / `ruff format`. JS/TS: ESLint +
  Prettier.
- **Types** — Python: `mypy` (gradual strictness, framework-aware stubs).
  TS: `tsc --noEmit`, `strict: true`, no `any` (use `unknown` + narrowing),
  avoid `as` casts.
- **TDD** — write the failing test first, then the implementation (red → green
  → refactor). Tests ship in the same commit/PR as the change they cover.
- **Tests** — Python: `pytest`. Frontend: Vitest. Names describe behaviour
  ("when X then Y"). Coverage is a **floor (~80%)**, not a goal.
- **Security** — dependency scanning + `gitleaks` for secrets as a hard CI
  block.
- **Pre-commit hooks** give local feedback; let them run (never `--no-verify`).

**In Dockerised repos, run tooling inside the container**, not on your host —
local versions drift from CI. For example, OctoHub:

```bash
docker compose exec backend bash -c "DJANGO_SETTINGS_MODULE=octohub.settings.test python -m pytest …"
docker compose exec backend ruff check .
docker compose exec frontend npx tsc --noEmit
```

Watch repo-specific footguns (each repo's `CLAUDE.md` lists them) — e.g. CI may
run tests on SQLite while local dev uses Postgres, and **Celery prefork workers
do not hot-reload**: restart them after changing polling/telemetry code.

---

## 6. Git discipline

- **Rebase, never merge** onto the target branch. No merge commits on `main`.
  ```bash
  git fetch origin && git rebase origin/main
  ```
- Force-pushing **feature** branches after a rebase is expected. **Never**
  force-push `main`.
- **Small, atomic commits.** Imperative subject ≤50 chars, no trailing period;
  body (wrapped ~72 chars) explains what and why, links tickets. Don't mix
  unrelated refactors with features. **No squashing** — each commit should stand
  on its own.

---

## 7. Secrets, migrations, observability

- **Secrets**: never commit credentials — not in code, tests, comments, or
  example configs. Runtime secrets via env vars; commit only `.env.example` with
  placeholders. If a secret leaks: **rotate immediately**, then scrub history.
- **Migrations**: backwards-compatible and reversible. Ship the migration first,
  verify, then ship the code that needs it — never bundle them. Destructive
  changes (drop/rename) need a deprecate → remove references → deploy → drop
  sequence. Write a `down` migration unless genuinely irreversible. Test against
  a copy of prod data.
- **Observability**: structured logs with correlation IDs (request/task/user
  id), consistent log levels, consistent API error envelopes, stack traces for
  unexpected errors. Never swallow exceptions silently. Redact secrets and PII
  from logs.

---

## 8. Deployment

- **Containerised runtimes with health checks.** Multi-stage Docker builds.
- **CI runs the full quality gate** on PRs to protected branches. Name workflows
  clearly (`*-ci.yml`, `*-deploy.yml`).
- **No deploy of unvalidated changes to production.** Environment-specific
  config for dev/staging/production.
- Common targets: **DigitalOcean App Platform** (FastAPI services, Postgres),
  **Vercel** (static/Next.js). Apply DB migrations as a pre-deploy step.
- Emergency hotfixes may bypass the normal flow **only** with a named approver,
  a recorded incident severity, and a follow-up task to restore the CI/CD path.

---

## 9. Exceptions and technical debt

Every rule here has documented escape hatches, but **waivers are temporary and
tracked**: an issue link, an owner, and an expiry or remediation milestone.
Typed escape hatches (`# type: ignore`, `any`) need a one-line justification.
Hotfixes that skip TDD or full gates need incident justification and a
follow-up. Silent debt is not acceptable; visible, tracked debt is.

---

## 10. Working as an agent on OEES code

- **Read before you write.** Start with this file, then the repo's `CLAUDE.md`
  and `README.md`. Use progressive disclosure — read only the docs you need.
- **Ask when unclear.** Don't default to the same framework or approach every
  time; confirm the choice fits the context.
- **Encourage cross-team communication.** When work touches another team's
  domain (CRM/Zoho, billing, Kraken, a partner integration), flag it so the
  right people are looped in.
- **Communicate simply and transparently.** Report outcomes faithfully — if
  tests fail, say so with the output; if you skipped a step, say that. Don't
  over-explain unless asked.
- **Don't do anything illegal**, and don't help anyone else to. Legal/compliance
  questions are fine to assist with.

---

*This document is a living reference. The authoritative, machine-loaded source
for behavioural rules is the `agents` repo's `.claude/rules/`; when in doubt,
that and the target repo's own `CLAUDE.md` take precedence over this summary.*
