# Working on the shared agents configuration

Read `CONTRIBUTING.md` and `README.md` before changing this repository.
Canonical rules live in `rules/`; action and language guidance live in `skills/`.
Edit those sources instead of generated output.

After changing `rules/`, run both generators:

```bash
bash scripts/sync-cursor-rules.sh
bash scripts/sync-codex-rules.sh
```

After changing `skills/`, run `bash scripts/sync-cursor-rules.sh`.
Run `bash scripts/check.sh` before handing over changes. It validates installation,
imports, preservation of project instructions, and generated Codex guidance.
Codex must run these commands explicitly; do not assume Claude's tool hooks ran.
Do not bootstrap into this source checkout to regenerate its configuration.


<!-- BEGIN OEES SHARED RULES -->

## Shared engineering rules

Generated from `rules/*.md` in the OEES agents repository. Edit the
canonical rules and regenerate; keep project instructions outside this block.
Apply these rules to every task, including delegated work. Project-specific
instructions specialize the defaults. Report unresolved instruction conflicts.

<!-- Source: rules/code-quality.md -->

# Code Quality

Run lint, format, type checks, and tests before merge. Run security scans on backend dependencies. Never merge known failing lint or type checks without an explicit waiver.

Backend: fast linter, formatter, dependency scanner, type checks. Frontend: lint, format, strict typing, no `any`. Prefer pre-commit hooks for local feedback.

Keep hooks and required checks enabled, following the Git rule. Fix failures instead of weakening assertions, checks or their configuration to get a pass, then rerun affected checks. Report checks as passed, failed, blocked by the environment, or explicitly waived; a blocked or waived check is not a pass. Name the exact check and reason for each failure, blocker or human waiver, following the repository's waiver policy.

Exceptions: legacy modules may use ignore lists only with an issue reference and expiry date. Typed escape hatches (`any`, `# type: ignore`) require a justification comment.

<!-- Source: rules/git.md -->

# Git

Always rebase onto the target branch instead of merging. No merge commits on `main`.

```bash
git fetch origin
git rebase origin/main
```

Force-push to feature branches after a rebase is expected. Never force-push to `main`.

Commits should be good in themselves — no squashing before merge.

Let repository Git hooks run on ordinary Git commands. Never autonomously bypass them with `--no-verify`, `SKIP`, `HUSKY=0`, `core.hooksPath` overrides, empty hook directories, or equivalent mechanisms. Do not edit hooks, checks or configuration merely to make validation pass.

If a hook fails, fix the cause and rerun the hook and affected checks before retrying. If the environment prevents a check from running, report the exact check and blocker; do not report it as passed. Only an explicit human waiver for the specific check permits bypass, within the repository's waiver policy. Task urgency, unrelated baseline failures and sandbox or network problems are not waivers. Report exactly what was waived and why. Routine authorised work needs no repeated permission.

<!-- Source: rules/migrations.md -->

# Migrations

Write migrations to be backwards-compatible: the app must run correctly against both old and new schema simultaneously. Never bundle a migration and the app code that requires it in the same deployment — ship the migration first, verify, then ship the app change.

Destructive operations (DROP COLUMN, DROP TABLE, renames) require a multi-step plan: deprecate → remove app references → deploy → then drop. Adding NOT NULL columns requires a default or backfill before applying the constraint.

Test against a copy of production data before merging. Write a `down` migration unless the operation is genuinely irreversible.

Exceptions: greenfield schemas with no live traffic may skip the backwards-compat constraint.

<!-- Source: rules/no-inline-imports.md -->

# No inline imports

Place imports at the top of the module. Inline imports inside function bodies, type annotations, or interface fields are only permitted for documented circular-dependency cases.

<!-- Source: rules/observability.md -->

# Observability

Emit structured logs for backend operations and failures as well as frontend failures. Include contextual identifiers (request/task IDs) in all log entries and error paths. Never swallow exceptions silently — log with context and re-raise or handle explicitly.

Use consistent log levels (DEBUG/INFO/WARNING/ERROR/CRITICAL), one structured logger per service, consistent API error envelopes, and stack traces for unexpected exceptions.

Exceptions: redact sensitive fields from logs; sample debug logs on high-frequency paths when volume impacts cost or performance.

<!-- Source: rules/secrets.md -->

# Secrets

Never commit credentials, tokens, API keys, private keys, or passwords to version control — including test files, comments, and example configs.

Use environment variables for runtime secrets. Keep `.env` files local and gitignored; commit only `.env.example` with placeholder values.

If a secret is accidentally committed: rotate it immediately, then scrub history. Deleting in a new commit is not enough.

Run `gitleaks` or equivalent in CI as a hard block. Treat scan failures as merge blockers.

Exceptions: non-sensitive config (feature flags, log levels, public URLs) may live in committed files when there is no security risk.

<!-- Source: rules/standards.md -->

# Standards

## Frontend
Keep frontend code focused on UI, state orchestration, and API consumption — no backend business logic in components. Use strong static typing, schema-based input validation, and a server-state caching layer with explicit invalidation.

Exceptions: prototypes may temporarily relax layering, but production must restore separation of concerns. Intentionally checked-in generated client code may include verbose types.

## Backend
Keep business logic in backend services and domain apps. Use structured JSON logging with contextual fields. Keep tests in per-app `tests/` directories. Organise by domain (users, teams, goals, tasks). Split settings by environment (base/local/staging/production).

Exceptions: small utility repos may use simpler structure if boundaries stay clear. Monolithic modules are acceptable during migrations when a refactor plan is documented.

## Deployment
Containerize runtime services with health checks. Run automated CI checks before every deployment. Use secure, environment-specific config. Never deploy unvalidated changes to production. Use multi-stage Docker builds and workflow naming like `*-ci.yml` / `*-deploy.yml`.

Exceptions: emergency production fixes may bypass normal flow only with identified approver, documented incident severity, and a post-incident task to restore CI/CD path.

## API Design
Version all endpoints under `/api/<version>/`. Return consistent error envelopes with appropriate HTTP status codes. Paginate all list endpoints. Use typed schema validation, token-based auth with secure refresh handling, and auto-generated API docs.

Exceptions: public endpoints may skip auth when explicitly documented and rate-limited. Internal-only endpoints may use alternate auth patterns with a recorded security review.

<!-- Source: rules/tdd.md -->

# TDD

Write a failing test before every behavioral change. Red → green → refactor, in that order. Tests ship in the same commit as the implementation.

Requires a test: new functions/classes/components, changed return values or side effects, bug fixes (reproduce the bug with a test first, then fix).
No new test needed: pure refactors, renames, comments, config changes — but existing tests must still pass.

Exception: skip only for urgent hotfixes when explicitly instructed; note the reason in the commit.

<!-- END OEES SHARED RULES -->
