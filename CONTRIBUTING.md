# Contributing to OEES code

This is the "why" document for every **Octopus Energy España (OEES)**
repository. It explains the philosophy behind the rules our engineers and our
AI coding agents (Claude Code, Cursor, Codex) follow. It is written for humans
and agents alike. How to install the shared tooling is covered in
[README.md](README.md); this document covers why the tooling says what it says.

---

## 1. Why this exists

Our job is to make energy *fair, clean and simple*, backed by outrageously good
service. The customer is the point. Everything else here (tests, reviews,
checks, logs, careful migrations) is how we keep that promise while moving
fast, and never at the customer's expense.

**Who reads this, and what wins.** Engineers joining an OEES repo, reviewers,
and agents starting a session. The project context block and the
`.oees-agents.toml` manifest always win over this document: they say what the
project is, who depends on it, which stack applies and which defaults it has
opted out of. Next come the project's own `CLAUDE.md` and `README.md`, then
this document.

---

## 2. What we believe

### The customer is the point

Every rule below serves the customer. Speed matters because customers are
waiting; safety matters because they trust us with their homes, their bills
and their data. Neither is an excuse to drop the other.

### Backend owns the truth

Business rules, validation, authorisation, persistence and computed outcomes
(KPIs, billing logic) live server-side. Clients orchestrate: they render, hold
UI state and call the API. A rule duplicated in a client drifts from the
server's copy, and then two screens disagree about what a customer owes.
Cosmetic derivation on the client is fine; authoritative rules are not.

### Small, reviewable changes

One logical change per commit, and every commit stands on its own. A reviewer
can only vouch for what they can hold in their head, and a bisect can only find
a regression in a commit that builds and passes. We rebase rather than merge
and we do not squash, so history reads as the sequence of decisions that
actually happened.

### Visible, tracked debt

Shortcuts are sometimes right. Hidden shortcuts never are. Every waiver carries
an issue, an owner and an expiry. Every typed escape hatch (`# type: ignore`,
`any`) carries a one-line justification. Silent debt is not acceptable; visible,
tracked debt is something we can plan to pay down.

### Checks are not negotiable

Hooks, linters, type checkers, tests and scanners exist because each one caught
something once. Never weaken or bypass them to get a pass. Fix the cause and
rerun. If the environment prevents a check from running, say exactly which and
why: a blocked or waived check is not a pass.

### Calibrate to the blast radius

Every project declares its blast radius in the manifest: `internal`,
`customer-facing` or `regulated`. Calibrate judgement calls (how much to test,
how cautious to be with data, how much review a change needs) to that context.
Never assume any code is a throwaway: internal tools still hold real data and
real people still depend on them.

---

## 3. Golden rules

1. **Never perform a write, delete or externally visible action without
   explicit permission from the human in the current interaction.** This
   covers pushing to a remote; deleting branches, files or database rows;
   opening, closing, commenting on or merging PRs and issues; sending messages
   (Slack, email); and editing `.env`, production configuration or any secret.
   Permission is **per specific action**: "yes, open the PR" does **not**
   authorise a later `git push --force`.
2. **Never merge PRs yourself.** A human reviews and merges from the GitHub UI.
3. **Never force-push the default branch.** Let Git hooks run normally. Never
   bypass or weaken hooks or required checks; fix failures and rerun them. Only
   a human's explicit waiver for a specific check permits bypass (§11).
4. **Spec first for new features** (§7). Bug fixes and minor refactors can go
   straight to a PR.
5. **Tests ship with the change** (§8). Write the failing test first.
6. **The customer is the point.** When a trade-off is unclear, choose the
   option that gives the customer the best, safest, most transparent outcome.

The machine-loaded source agents actually read is `content/conduct/conduct.md`,
together with `content/conduct/secrets.md`. Both are always on and cannot be
opted out of. If this prose and `conduct.md` disagree, `conduct.md` wins and
this section should be fixed.

---

## 4. The shared tooling

All OEES repos share one set of rules, skills, slash commands and subagents,
maintained in the `oees/agents` repo. The `oees-agents` installer asks a project
a few questions once, records the answers in `.oees-agents.toml`, and generates
the Claude Code, Cursor and Codex files from that manifest. Re-runs are driven
by the manifest and never re-add what a project removed.

```bash
uvx --from git+https://github.com/oees/agents@v1.0.0 oees-agents init
git add .oees-agents.toml .oees-agents.lock AGENTS.md .claude/ .cursor/
git commit -m "Add shared AI engineering guidance"
```

`npx @oees/agents init` runs the same CLI for teams that prefer npm. Updating,
flags, the manifest format and everything else about installation are in
[README.md](README.md).

Content comes in three tiers. **Conduct** is always on: the short list no
project may opt out of. **Defaults** are the OEES way, on for every project; a
project opts out of one individually, with a one-line reason comment in its
manifest. **Kits** are opted into per stack and carry that stack's concrete
layout, settings, templates and commands.

### Conduct (always on)

Generated from `content/` by `make docs`; do not edit by hand (`make check` fails if stale).
<!-- BEGIN GENERATED: conduct -->
| Rule | What it covers |
|---|---|
| `conduct` | Always-on conduct — per-action permission for visible actions, never merge, hooks and checks never bypassed, faithful reporting |
| `data-protection` | Personal data stays out of logs, traces, errors, fixtures and prompts |
| `secrets` | Never commit secrets; use env vars and secret managers |
<!-- END GENERATED: conduct -->

### Defaults (opt out per project)

Generated from `content/` by `make docs`; do not edit by hand (`make check` fails if stale).
<!-- BEGIN GENERATED: defaults -->
| Rule | What it covers |
|---|---|
| `api` | Versioned endpoints, consistent error envelopes, pagination, typed validation, token auth, generated docs |
| `git` | Rebase onto the default branch, no merge commits, no squashing, commits that stand alone |
| `migrations` | Safe, backwards-compatible database schema migrations |
| `observability` | Structured logging, contextual errors, no silent exceptions |
| `quality-gates` | Lint, format, types, tests and dependency scan before merge, run through make check and make check-fast |
| `standards` | Backend owns the truth, organise by domain, frontend orchestrates, validated deploys |
| `tdd` | TDD: write failing tests before implementation, red-green-refactor |
<!-- END GENERATED: defaults -->

### Kits

Generated from `content/` by `make docs`; do not edit by hand (`make check` fails if stale).
<!-- BEGIN GENERATED: kits -->
| Kit | What it is for |
|---|---|
| `django-drf` | Use when building or changing a Django + Django REST Framework service, its Celery workers, or how it is tested, containerised and deployed to DigitalOcean App Platform. |
| `fastapi` | Use when building or changing a FastAPI service (API-only backends, middleware to external services, embeddable widget backends) in an OEES project. |
| `htmx-alpine` | Use when building or reviewing server-rendered Django screens with htmx and Alpine, covering templates, partials, forms, static assets, CSP, translations and accessibility. |
<!-- END GENERATED: kits -->

### Subagents

Generated from `content/` by `make docs`; do not edit by hand (`make check` fails if stale).
<!-- BEGIN GENERATED: subagents -->
| Subagent | Set | What it does |
|---|---|---|
| `engineering-reviewer` | core | Use on every code change, after the simplifier, to review maintainability in a fresh, read-only context: the code-review bar plus domain boundaries, layering, atomicity, error handling, logging and test quality. Give it the requirement, the diff with its base and head, and the output of the checks run on that head. |
| `functional-reviewer` | core | Use on every behavioural change, after the simplifier, to check in a fresh, read-only context that the change does what the requirement says — no less, no more. Give it the requirement (the accepted spec, ticket or requirements record, or the task's stated requirement) and its acceptance cases, the diff with its base and head, the red and green test output, and the checks run on that head. |
| `implementer` | core | Use for the green step after the test-writer has produced failing tests. Makes those tests pass within its assigned paths, which decide the surface (backend code, UI code or both). Several may run in parallel on paths that do not overlap. Give it the failing tests and their red output, the requirement, its paths and any contract it depends on. |
| `security-reviewer` | core | Use, in a fresh read-only context, on any change touching authentication, authorisation, PII, secrets, exposed endpoints, uploads, dependencies, workflows or agent protections (.claude/, .agents/, hooks, settings). Give it the requirement, the diff with its base and head, and the output of the checks run on that head, including the secret scan and the dependency scan. |
| `simplifier` | core | Use on every code change once the tests are green and before the reviewers. In a fresh context, simplifies the task's changed code without changing behaviour, then repeats the affected checks. Give it the requirement, the authorised paths and the diff range to simplify, not the implementer's reasoning. |
| `test-writer` | core | Use for the red step of every behavioural change or bug fix, before any implementation. Derives acceptance cases from the requirement and writes failing tests, plus signature-only stubs where needed. Give it the requirement, the acceptance cases and the target paths. |
| `docs-verifier` | extended | Use, in a fresh read-only context, on every docs change beyond a typo, and always after rewording, splitting or moving files. Checks that the change kept its meaning, ownership and links. Never run it on a change it wrote. Give it the diff with its base and head (with renames detected, so old text is visible), and the documentation writer's list of intended changes. |
| `documentation-writer` | extended | Use for every docs change: recording a human decision, updating docs a code change made stale, restructuring or rewording, and drafting requirement records. Writes in the owning file and keeps links, tags and indexes consistent. Give it what changed or what was decided (with who and when), the scope, and the owning files if known. |
| `infra-implementer` | extended | Use for infrastructure and delivery code: infrastructure as code, platform app specs, CI workflows, the Dockerfile, the Makefile and tool configuration. Writes code and runs local checks; never applies changes or touches live infrastructure. Give it the requirement, the authorised scope and its paths. |
| `infra-reviewer` | extended | Use, in a fresh read-only context, on every change to infrastructure code, CI workflows, the Dockerfile, the Makefile or tool configuration. Give it the requirement, the diff with its base and head, the infrastructure plan posted by CI when available, and the output of the project's infrastructure checks (its validators, linters and security scanners). |
| `migration-reviewer` | extended | Use, in a fresh read-only context, on every change containing a schema migration, data-import code or a destructive data operation. Give it the requirement, the diff with its base and head, the migration linter output if the project has one, and the checks run on that head against the real database engine. |
| `ui-reviewer` | extended | Use, in a fresh read-only context, on every change to templates, components, client code, static assets or the views that render them. Give it the requirement, the diff with its base and head, and the output of the checks run on that head, including template and frontend linters, type checks, translation checks and any browser test runs. |
<!-- END GENERATED: subagents -->

### Slash commands

Generated from `content/` by `make docs`; do not edit by hand (`make check` fails if stale).
<!-- BEGIN GENERATED: commands -->
| Command | What it does |
|---|---|
| `/code-review` | Run an extremely strict maintainability review for abstraction quality, giant files, and spaghetti-condition growth. Use for a code quality review or a code audit. |
| `/commit` | Create a well-formed git commit following team standards — atomic scope, imperative subject ≤50 chars, body explaining what/why, 72-char line wrap. Use when the user asks to commit, wants to write a commit message, or invokes /commit. |
| `/plan` | Write an implementation plan from a spec or requirements before touching code — one commit-sized task at a time, each naming its files and its failing test. Use when given a spec, a feature brief, or a multi-step task to plan out. |
| `/pr-tidy` | Prepare PRs for review by cleaning noisy history, improving PR descriptions, and adding reviewer guidance without changing code behavior. Use for "make this easy to review", "tidy this PR", "clean up commits", or "annotate the diff". |
| `/shipped` | Summarize everything the user has personally authored and shipped across all local git repositories in a configurable time period. Use when the user asks "what did I ship?", "what have I worked on?", or wants a personal activity summary. |
| `/test` | Write well-structured tests following TDD. Test design, mocking discipline, naming, and coverage decisions. Use when writing tests or reviewing test quality. |
<!-- END GENERATED: commands -->

Some repos add their own (for example OctoHub has `/create-pr` and
`/sync-github`). Prefer a repo's own PR and sync skills when present.

---

## 5. The repositories at a glance

| Repo | What it is | Stack | Kits |
|---|---|---|---|
| `octosentinel` | Multi-vendor energy-device monitoring platform (3,000+ plants, scaling to 50k+) | Django 5 + DRF, Celery, RabbitMQ, Redis, TimescaleDB/PostgreSQL 15, MQTT (Mosquitto), React 18 + Vite | `django-drf` |
| `octohub` | B2B multi-tenant platform for selling/installing energy products (Partners + Vendors) | Django 5 + DRF, Celery, Redis 7, PostgreSQL 16, React 19 + TS + Vite + Tailwind + TanStack Query | `django-drf` |
| `franklin` | Web app for OEES ambassadors to create energy accounts in Kraken | Django 6, Bootstrap 5 + vanilla JS, PostgreSQL, Kraken GraphQL API | `django-drf`, `htmx-alpine` |
| `hermes` | Middleware to external services (Zoho CRM, etc.): OAuth, retries, webhooks | FastAPI, SQLAlchemy 2.0, Celery, HTTPX, PostgreSQL | `fastapi` |
| `bill-e` | Microservice: PDF electricity bill to plain-language explanation via local LLM | FastAPI, `uv`, pytest/hypothesis | `fastapi` |
| `consumer-site-embeds` | Embeddable widgets (e.g. World Cup vote) | FastAPI, async SQLAlchemy + asyncpg, Alembic, Docker, DigitalOcean App Platform | `fastapi` |
| `octopanel` | Internal panel (brand/design assets) | — | — |
| `vercel-deployer` | Internal app to publish pre-built static sites to Vercel without git | Next.js, TypeScript | — |

**Patterns you'll see repeatedly:** Django + DRF or FastAPI on the backend;
Celery + Redis/RabbitMQ for async work; PostgreSQL (TimescaleDB for telemetry);
React + TypeScript + Vite + TanStack Query on the frontend, or server-rendered
HTMX + Alpine; everything runs in **Docker**; deploys target **DigitalOcean App
Platform** or **Vercel**.

---

## 6. Architecture conventions

- **Backend owns the truth** (§2). Business rules, validation, authorisation,
  persistence and computed outcomes live in backend services and domain apps,
  never duplicated in clients.
- **Organise by domain, not by technical layer.** Files that change together
  live together. Test layout follows the kit the project uses.
- **Settings are split by environment**: `base` / `local` / `test` /
  `production`, with `staging` only where a project has one.
- **Frontend** handles UI, state orchestration and API calls only. Strong
  static typing, schema validation at boundaries, a server-state cache with
  explicit invalidation rather than local state for server data.
- **API design**: version under `/api/<version>/`, consistent error envelopes
  with correct HTTP status codes, paginate every list endpoint, typed schema
  validation, token-based auth with secure refresh, auto-generated docs.
- **Stack specifics live in kits.** Framework layout, logging config, container
  and deploy templates are in the kit, not in the org-wide rules.
- **Multi-tenancy** (where it applies, e.g. octosentinel and octohub): every
  governance row carries a `tenant_id`; enforce tenant scoping at the queryset
  level in every ViewSet.

---

## 7. Workflow: spec, plan, implement, PR

1. **New feature: write a spec first.** A self-contained doc (typically
   `docs/specs/<feature>.md`) with a **Vision** section (problem, goal, actors,
   out of scope) and a **Design** section (decisions, API or contract, changes
   per layer, risks, tests, open items). A human reviews and approves it
   **before** you implement. Bug fixes and minor refactors skip the spec.
2. **Plan it.** Use `/plan` to turn the spec into commit-sized tasks, each
   naming its files and the failing test to write first.
3. **Implement in small, reviewable PRs**, each with human approval. One
   logical change per commit.
4. **Open the PR** with the repo's PR skill (such as `/create-pr`) or
   `/pr-tidy`, using the Octopus PR template. A human merges from the GitHub UI.

---

## 8. Quality gates (non-negotiable before merge)

Run the **same checks locally and in CI**. Use `make check-fast` (lint,
format, types, targeted tests) while working and `make check` (the full gate)
before handing over. Every kit ships both targets; the project context names
the actual commands where a project differs.

- **Lint and format**: Python `ruff check` / `ruff format`; JS/TS ESLint +
  Prettier.
- **Types**: Python `mypy` (gradual strictness, framework-aware stubs); TS
  `tsc --noEmit` with `strict: true`, no `any` (use `unknown` and narrowing),
  avoid `as` casts.
- **TDD**: write the failing test first, then the implementation (red, green,
  refactor). Tests ship in the same commit as the change they cover.
- **Tests**: Python `pytest`; frontend Vitest. Names describe behaviour ("when
  X then Y"). Coverage is a **floor (~80%)**, not a goal.
- **Security**: dependency scanning, and `gitleaks` for secrets as a hard CI
  block.

**Git hooks must run normally.** Never autonomously use `--no-verify`, `SKIP`,
`HUSKY=0`, `core.hooksPath` overrides, empty hook directories or equivalent
bypasses. Do not edit hooks, assertions, checks or configuration merely to make
validation pass. Fix the cause, rerun the hook and affected checks, then retry.
If the environment prevents a check from running, report the exact check and
blocker. A blocked or explicitly waived check is not a pass; identify any human
waiver and follow §11. Routine authorised checks need no fresh approval.

**In Dockerised repos, run tooling inside the container**, not on your host;
local versions drift from CI (for example `docker compose exec <service> make
check-fast`). Watch repo-specific footguns, which each repo's `CLAUDE.md`
lists: CI may run tests on a different database engine than local dev, and
Celery prefork workers do not hot-reload.

---

## 9. Git discipline

- **Rebase, never merge**, onto the default branch. Detect it rather than
  hard-coding it:
  ```bash
  git fetch origin
  git rebase "$(git rev-parse --abbrev-ref origin/HEAD)"
  ```
- **No merge commits and no squashing.** Each commit should stand on its own.
  Squash-merge is a per-project opt-in.
- Force-pushing **feature** branches after a rebase is expected. **Never**
  force-push the default branch.
- **Small, atomic commits.** Imperative subject of 50 characters or fewer, no
  trailing period; body (wrapped at about 72 characters) explains what and why
  and links tickets. Don't mix unrelated refactors with features.

---

## 10. Secrets, migrations, observability

- **Secrets**: never commit credentials, not in code, tests, comments or
  example configs. Runtime secrets come from environment variables; commit only
  `.env.example` with placeholders. If a secret leaks: **rotate immediately**,
  then scrub history. Deleting it in a new commit is not enough.
- **Migrations**: backwards-compatible and reversible. Ship the migration
  first, verify, then ship the code that needs it; never bundle them.
  Destructive changes (drop, rename) need a deprecate, remove references,
  deploy, drop sequence. Write a `down` migration unless genuinely
  irreversible. Test against a copy of production data.
- **Observability**: structured logs with correlation ids (request, task,
  user), consistent log levels, consistent API error envelopes, stack traces
  for unexpected errors. Never swallow exceptions silently. Redact secrets and
  PII from logs.

### Deployment

- **Containerised runtimes with health checks.** Multi-stage Docker builds.
- **CI runs the full quality gate** on PRs to protected branches. Name
  workflows clearly (`*-ci.yml`, `*-deploy.yml`).
- **No deploy of unvalidated changes to production.** Configuration is
  environment-specific.
- Common targets: **DigitalOcean App Platform** (Django and FastAPI services,
  Postgres) and **Vercel** (static and Next.js). Apply database migrations as a
  pre-deploy step.
- The kits ship the concrete templates: Dockerfile, compose file, CI workflow,
  health endpoint and, for the backend kits, the App Platform spec.
- Emergency hotfixes may bypass the normal flow **only** with a named approver,
  a recorded incident severity, and a follow-up task to restore the CI/CD path.

---

## 11. Exceptions and technical debt

Every rule here has documented escape hatches, but **waivers are temporary and
tracked**: an issue link, an owner, and an expiry or remediation milestone.
Typed escape hatches (`# type: ignore`, `any`) need a one-line justification.
Hotfixes that skip TDD or full gates need incident justification and a
follow-up. Opting a project out of a default is recorded in its manifest with a
one-line reason. Silent debt is not acceptable; visible, tracked debt is.

---

## 12. Working as an agent on OEES code

- **Read before you write.** Start with the project context block, then the
  repo's `CLAUDE.md` and `README.md`, then this file for the reasoning behind a
  rule. Read only the docs you need.
- **Know the stack.** The project context says which stack and kits apply.
  Ask only when it is missing.
- **Encourage cross-team communication.** When work touches another team's
  domain (CRM/Zoho, billing, Kraken, a partner integration), flag it so the
  right people are looped in.
- **Communicate simply and transparently.** Report outcomes faithfully: if
  tests fail, say so with the output; if you skipped a step, say that. Don't
  over-explain unless asked.
- **Don't do anything illegal**, and don't help anyone else to. Legal and
  compliance questions are fine to assist with.

---

## 13. Changing this repo

- **A rule** is a `.md` file under `content/conduct/` or `content/defaults/`
  with `name` and `description` frontmatter. Conduct is deliberately short;
  add to it only what no project should ever be able to opt out of. Every
  default opens with "Default for OEES projects. A project opts out in its
  manifest."
- **A skill** is `skills/<name>/SKILL.md` with `name` and `description`
  frontmatter. A skill backed by a slash command also gets `commands/<name>.md`,
  which imports `@../skills/<name>/SKILL.md`.
- **A kit** is `content/kits/<name>/SKILL.md` plus `templates/`. The SKILL.md
  covers, in this order: layout, settings, logging, errors, tests, Makefile
  targets, container, deploy path, and says which template to copy for each.
  Templates are real files a project can copy unchanged, and every kit ships
  both `make check` and `make check-fast`.
- **A subagent** goes in `content/subagents/core/` or
  `content/subagents/extended/`. It contains no project vocabulary (refer to
  "the fast checks named in the project context", not a specific command or
  tool) and preloads the skills it needs through `skills:` frontmatter rather
  than copying their text.

Then run `make docs` to regenerate the tables above and `make check` before
opening a PR. Commits stand alone, as everywhere else. Releases are cut by
pushing a `v*` tag, which runs the release workflow; never publish by hand.

---

*This is a living reference; the machine-loaded source is `content/`.*
