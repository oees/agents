# Working on the shared agents configuration

Read `CONTRIBUTING.md` and `README.md` before changing this repository.
Canonical rules live in `content/conduct/` (always on) and `content/defaults/`
(opt-out); action and language guidance live in `skills/`. Edit those sources
instead of generated output.

After changing `content/conduct/` or `content/defaults/`, run both generators:

```bash
bash scripts/sync-cursor-rules.sh
bash scripts/sync-codex-rules.sh
```

After changing `skills/`, run `bash scripts/sync-cursor-rules.sh`.
Run `bash scripts/check.sh` before handing over changes. It validates installation,
imports, preservation of project instructions, and generated Codex guidance.
Run `uv run pytest` too: the content lint tests guard skill layout, skill
references, loop sections and generic subagent wording.
Codex must run these commands explicitly; do not assume Claude's tool hooks ran.
Do not bootstrap into this source checkout to regenerate its configuration.


<!-- BEGIN OEES SHARED RULES -->

## Shared engineering rules

Generated from `content/conduct/` and `content/defaults/` in the OEES agents
repository. Edit the canonical rules and regenerate; keep project
instructions outside this block.
Apply these rules to every task, including delegated work. Project-specific
instructions specialize the defaults. Report unresolved instruction conflicts.

<!-- Source: content/conduct/conduct.md -->

# Conduct

Always on in every OEES project. These rules have no opt-out.

## Permission

Take no externally visible action without explicit permission from the human for that specific action: pushing, merging, opening, closing or commenting on pull requests and issues, sending messages, deleting branches, files or data, and editing secrets or production configuration. Permission is per action: "yes, open the PR" does not authorise a later force-push. Routine work the task already authorises, such as editing files, running checks and committing locally, needs no repeated permission.

## Never

- Never merge a pull request. A human reviews and merges.
- Never force-push the default branch or rewrite its history.

## Hooks and checks

Let Git hooks and required checks run on ordinary commands. Never bypass them (`--no-verify`, `SKIP`, `HUSKY=0`, `core.hooksPath` overrides, empty hook directories or equivalents), and never weaken assertions, checks or their configuration to get a pass. When one fails, fix the cause, then rerun it and the affected checks.

Report each check as passed, failed, blocked by the environment or explicitly waived, naming the exact check and the reason. A blocked or waived check is not a pass. Only an explicit human waiver for a specific check permits a bypass, within the project's waiver policy; urgency, unrelated baseline failures and sandbox or network problems are not waivers.

## Reporting

Report outcomes faithfully. If tests fail, say so with the output. If you skipped a step, say which and why. Never describe work as done or verified when it is not.

<!-- Source: content/conduct/data-protection.md -->

# Data protection

Personal data is any value identifying a person alone or combined with another: name, email, phone, address, DNI/NIE, IBAN, CUPS and meter serial, geolocation, consumption tied to a supply point. Log the surrogate id (account, supply, request, task) instead.

Never write it to a sink that outlives the request: logs and log context, traces, span attributes, metric labels, exception messages, URLs, cache keys, queue arguments, analytics events, alerts, tickets, or prompts sent to a model or external API.

Redact at one boundary per service, not at each call site, and prove it with a test that sends a known value through the real pipeline and asserts it never reaches the sink. An untested convention is not a safeguard.

Serializers, exports and outbound payloads carry the fields the caller needs and no more. Fixtures, docs, screenshots and agent prompts use synthetic or approved anonymised data. Every store holding personal data needs a retention period and an erasure path that reaches it.

A leak is an incident: tell the data protection officer (dpd@octopusenergy.es) the same day, purge the sink, then close the path. Deleting the line in a later commit is not enough.

Exceptions: the system of record stores what its lawful basis allows, and the UI shows it to an authorised user. Debugging with real data needs a named approver, an access-controlled destination and a deletion deadline.

<!-- Source: content/conduct/secrets.md -->

# Secrets

Never commit credentials, tokens, API keys, private keys, or passwords to version control — including test files, comments, and example configs.

Use environment variables for runtime secrets. Keep `.env` files local and gitignored; commit only `.env.example` with placeholder values.

If a secret is accidentally committed: rotate it immediately, then scrub history. Deleting in a new commit is not enough.

Run `gitleaks` or equivalent in CI as a hard block. Treat scan failures as merge blockers.

Exceptions: non-sensitive config (feature flags, log levels, public URLs) may live in committed files when there is no security risk.

<!-- Source: content/defaults/api.md -->

# API design

Default for OEES projects. A project opts out in its manifest.

Version all endpoints under `/api/<version>/`. Return consistent error envelopes with appropriate HTTP status codes. Paginate all list endpoints. Use typed schema validation, token-based auth with secure refresh handling, and auto-generated API docs.

Exceptions: public endpoints may skip auth when explicitly documented and rate-limited. Internal-only endpoints may use alternate auth patterns with a recorded security review.

<!-- Source: content/defaults/git.md -->

# Git

Default for OEES projects. A project opts out in its manifest.

Always rebase onto the target branch instead of merging. No merge commits on the default branch. Detect the default branch rather than assuming its name; the project context names it, and Git reports it:

```bash
git rev-parse --abbrev-ref origin/HEAD   # e.g. origin/main
git fetch origin
git rebase origin/<default-branch>
```

Force-pushing a feature branch after a rebase is expected. Never force-push the default branch.

Commits should be good in themselves: one logical change each, building and passing on their own. No squashing before merge, unless the project's manifest opts into squash-merge.

Hooks run on every Git command, as the conduct rule requires. If a hook fails, fix the cause and rerun the hook and the affected checks before retrying.

<!-- Source: content/defaults/migrations.md -->

# Migrations

Default for OEES projects. A project opts out in its manifest.

Write migrations to be backwards-compatible: the app must run correctly against both old and new schema simultaneously. Never bundle a migration and the app code that requires it in the same deployment — ship the migration first, verify, then ship the app change.

Destructive operations (DROP COLUMN, DROP TABLE, renames) require a multi-step plan: deprecate → remove app references → deploy → then drop. Adding NOT NULL columns requires a default or backfill before applying the constraint.

Test against a copy of production data before merging. Write a `down` migration unless the operation is genuinely irreversible.

Exceptions: greenfield schemas with no live traffic may skip the backwards-compat constraint.

<!-- Source: content/defaults/observability.md -->

# Observability

Default for OEES projects. A project opts out in its manifest.

Emit structured logs for backend operations and failures as well as frontend failures. Include contextual identifiers (request/task IDs) in all log entries and error paths. Never swallow exceptions silently — log with context and re-raise or handle explicitly.

Use consistent log levels (DEBUG/INFO/WARNING/ERROR/CRITICAL), one structured logger per service, consistent API error envelopes, and stack traces for unexpected exceptions.

Exceptions: redact sensitive fields from logs; sample debug logs on high-frequency paths when volume impacts cost or performance.

<!-- Source: content/defaults/quality-gates.md -->

# Quality gates

Default for OEES projects. A project opts out in its manifest.

Run lint, format, type checks, tests and a dependency vulnerability scan before every merge, with the same commands locally and in CI. Never merge with a known failing check unless a human has waived that specific check.

Every project exposes two commands, named in its project context (by default):

- `make check-fast`: lint, format, types and the tests affected by the change. Run it while working and before each commit.
- `make check`: everything CI runs, including the full test suite and the dependency scan. Run it before handing work over.

Backend: a fast linter and formatter, a type checker and a dependency scanner. Frontend: lint, format and strict typing with no `any`. Prefer pre-commit hooks for local feedback.

Exceptions: legacy modules may use ignore lists only with an issue reference and an expiry date. Typed escape hatches (`any`, `# type: ignore`) require a justification comment.

<!-- Source: content/defaults/standards.md -->

# Standards

Default for OEES projects. A project opts out in its manifest.

## Backend owns the truth

Business rules, validation, authorisation, persistence and computed outcomes (prices, KPIs, billing) live in backend services and domain modules, never duplicated in clients.

## Organise by domain

Group code by business domain, not by technical layer. Files that change together live together. The project's kit sets the stack's layout, settings modules and test locations.

Exceptions: small utility repos may use simpler structure if boundaries stay clear. Monolithic modules are acceptable during migrations when a refactor plan is documented.

## Frontend orchestrates

Keep frontend code to UI, state orchestration and API consumption, with no backend business logic in components. Use strong static typing, schema-based input validation and a server-state cache with explicit invalidation. Cosmetic derivation on the client is fine.

Exceptions: prototypes may temporarily relax layering, but production must restore separation of concerns. Intentionally checked-in generated client code may include verbose types.

## Deployment

Run CI checks before every deployment and never deploy unvalidated changes to production. Keep configuration secure and specific to each environment.

Exceptions: emergency production fixes may bypass normal flow only with an identified approver, a documented incident severity, and a post-incident task to restore the CI/CD path.

<!-- Source: content/defaults/tdd.md -->

# TDD

Default for OEES projects. A project opts out in its manifest.

Write a failing test before every behavioral change. Red → green → refactor, in that order. Tests ship in the same commit as the implementation.

Requires a test: new functions/classes/components, changed return values or side effects, bug fixes (reproduce the bug with a test first, then fix).
No new test needed: pure refactors, renames, comments, config changes — but existing tests must still pass.

Exception: skip only for urgent hotfixes when explicitly instructed; note the reason in the commit.

<!-- END OEES SHARED RULES -->
