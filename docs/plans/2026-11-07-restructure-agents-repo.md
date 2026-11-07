# Restructure the agents repo: opt-in tooling, honest context, generic agents

**Goal:** Turn the all-or-nothing bootstrap into an opt-in installer, stop telling agents they work on throwaways, make the subagents and skills generic, and give every project a way to pick exactly the tooling it wants while keeping the Octopus Energy España way as the default.

**Architecture:** One Python CLI (`oees-agents`, run through `uvx`) reads canonical content from this repo, asks the project a few questions once, writes a manifest (`.oees-agents.toml`) and generates the Claude Code, Cursor and Codex files from it. Re-runs are driven by the manifest and never re-add what a project removed. Content is split into three tiers: conduct (always on), defaults (opt-out), kits (opt-in). A managed project-context block replaces the "internal tool for a handful of staff" banner.

**Tech stack:** Python 3.11+, uv, typer, questionary, tomllib/tomli-w, pytest. An npm shim (`@oees/agents`) that execs the same CLI. GitHub Actions for CI.

---

## Decisions recorded on 2026-11-07 (Enrique Tasa)

| Topic | Decision |
|---|---|
| Settings split | `base / local / test / production`; staging only where a project has one |
| Git flow | Rebase, no squash; default branch detected, never hard-coded; squash-merge is a per-project opt-in |
| Quality gate | `make check` (full) and `make check-fast` (lint, format, types, targeted tests); every kit ships both targets |
| Test layout | Defined per kit; the org rule says "follow the kit" |
| Installer | Python CLI via `uvx`; npm shim for compatibility; one implementation, two entry points |
| Rule tiers | Conduct (always on) and defaults (opt-out individually) |
| Project context | Collected at install, injected as a managed block; banner removed everywhere |
| Subagents | Core six by default, four specialists opt-in; project vocabulary replaced by context references |
| First kits | `django-drf`, `fastapi`, `htmx-alpine` |
| Pattern skills | Rewritten as SKILL.md stating the Octopus stack as the default |
| Plan skill | Lighter: commit-sized tasks, no announce line, no execution handoff |
| Generated files | settings.json generated per project from the manifest; `.cursor/*.mdc` generated at install, not committed here |

Defaults I have taken without asking; veto any of them in review:

- Manifest file name is `.oees-agents.toml` at the project root, committed.
- Installs resolve to the latest git tag by default; `--ref main` overrides.
- `no-inline-imports` folds into the Python pattern skill (it is Python-specific).
- `code-quality` splits: the "never weaken checks" part joins conduct, the gates list joins defaults.
- `standards` splits: API conventions become their own default rule (`api`), stack specifics move to kits, what remains is the layering philosophy.
- Loops stay as opt-in templates. The global `install.sh` path is dropped; a later `oees-agents init --global` can replace it if anyone misses it.
- `rm` is no longer denied in generated settings. Denied: `git push`, `git push --force`, `git reset --hard`, `git rebase -i`, `git filter-branch`.

---

## Target layout

```
agents/
  pyproject.toml                      oees-agents CLI (uv-managed)
  Makefile                            check, check-fast (dogfoods the kit convention)
  src/oees_agents/
    cli.py                            init, update, check, list
    manifest.py                       read/write/validate .oees-agents.toml
    questions.py                      interactive prompts, all skippable with flags
    content.py                        loads tiers, skills, kits, subagents, loops
    render.py                         builds the file set for a manifest
    targets/claude.py                 .claude/CLAUDE.md, rules/, skills/, commands/, agents/, settings.json
    targets/cursor.py                 .cursor/rules/*.mdc
    targets/codex.py                  AGENTS.md managed block
    legacy.py                         detects and migrates pre-manifest installs
  tests/                              pytest; one file per module plus content lint tests
  npm/                                @oees/agents shim (package.json + bin/oees-agents.js)
  content/
    conduct/                          tier 1: conduct.md, secrets.md
    defaults/                         tier 2: tdd.md, git.md, observability.md, migrations.md, api.md, standards.md, quality-gates.md
    skills/<name>/SKILL.md            commit, code-review, plan, pr-tidy, test, shipped, python-patterns, typescript-patterns, reviewing
    kits/<name>/SKILL.md + templates/ django-drf, fastapi, htmx-alpine
    subagents/core/*.md               test-writer, implementer, simplifier, functional-reviewer, engineering-reviewer, security-reviewer
    subagents/extended/*.md           migration-reviewer, infra-implementer, infra-reviewer, ui-reviewer, documentation-writer, docs-verifier
    loops/*.md
    blocks/project-context.md.j2      the managed context block
  docs/plans/
  README.md                           install and what you get
  CONTRIBUTING.md                     the "why": philosophy, with rule tables generated from content/
```

The manifest a project ends up with:

```toml
version = 1
source = "v1.0.0"
targets = ["claude", "cursor", "codex"]

[project]
name = "octohub"
description = "B2B multi-tenant platform where partners and vendors sell and install energy products."
users = "external partners, vendors, OEES operations"
blast_radius = "customer-facing"     # internal | customer-facing | regulated
default_branch = "main"
check = "make check"
check_fast = "make check-fast"

[rules]
defaults = ["tdd", "git", "observability", "migrations", "api", "standards", "quality-gates"]

[kits]
enabled = ["django-drf", "htmx-alpine"]

[extras]
commands = true
subagents = "core"                  # none | core | extended
loops = []
```

The generated context block, placed at the top of `.claude/CLAUDE.md`, inside the Codex block in `AGENTS.md`, and as `.cursor/rules/00-project-context.mdc`:

```markdown
<!-- BEGIN OEES PROJECT CONTEXT -->
## Project context
**octohub** is a B2B multi-tenant platform where partners and vendors sell and install energy products.
Used by: external partners, vendors, OEES operations. Blast radius: customer-facing.
Stack: django-drf, htmx-alpine. Default branch: main.
Checks: `make check-fast` while working, `make check` before handing over.
Calibrate every judgement call to this context. Never assume the code is a throwaway.
<!-- END OEES PROJECT CONTEXT -->
```

---

## Phase 1: Content (no installer changes yet, bash scripts keep working at every commit)

### Task 1.1: Content lint tests that fail today

**Files:**
- Create: `tests/test_content_lint.py`
- Create: `pyproject.toml` (pytest only for now; the CLI package comes in Phase 2)

Tests, all red against the current tree:

- `no_file_claims_the_project_is_a_throwaway`: no file under `content/`, `skills/`, `loops/`, `subagents/` contains "internal tool for a handful of staff" or "internal tool for a small team".
- `every_skill_is_a_SKILL_md`: every directory under `skills/` and `content/skills/` holds exactly one `SKILL.md` with `name` and `description` frontmatter.
- `no_dangling_skill_references`: every `@../skills/...` import and every `skills:` frontmatter entry in a subagent resolves.
- `loops_have_no_duplicated_sections`: no loop file repeats an `## ` heading.
- `subagents_contain_no_project_vocabulary`: a deny-list (`make check-fast`, `Testcontainers`, `Squawk`, `zizmor`, `OpenTofu`, `HTMX`, `DECIDED`, `DERIVED`, `tech lead`, `doctl`, `import contracts`) does not appear in `subagents/`.

These tests go green task by task below. Commit: `Add content lint tests for the restructure`.

### Task 1.2: Fix the duplicated tier-0 loop

**Files:** Modify `loops/tier-0-daily-health-scan.md`

Delete the second copy of everything from `## De-duplication` to the end. Green: `loops_have_no_duplicated_sections`. Commit: `Remove duplicated tail of the tier-0 loop`.

### Task 1.3: Rename skills to SKILL.md and strengthen the pattern skills

**Files:**
- Rename: `skills/<name>/<name>.md` to `skills/<name>/SKILL.md` for all eight
- Modify: `commands/*.md` imports to `@../skills/<name>/SKILL.md`
- Modify: `scripts/sync-cursor-rules.sh`, `scripts/check.sh`, `scripts/install.sh` to the new file name
- Rewrite: `skills/python-patterns/SKILL.md`, `skills/typescript-patterns/SKILL.md`

The rewritten pattern skills say what we do and why, and defer stack detail to kits:

- Python: "Backend services are Django + DRF for full-stack and admin-heavy products, FastAPI for API-only services and middleware. The project context says which; do not ask unless it is missing." Keep: async guidance, type hints, Pydantic at boundaries, domain exceptions, N+1, background work (Celery for persistent queues). Add: imports at module top (absorbs `no-inline-imports`), structlog-style structured logging, settings split `base/local/test/production`. Remove: the framework decision tree, Flask, "never default to the same framework".
- TypeScript: "Frontends are React + TypeScript + Vite with TanStack Query; server-rendered projects use HTMX + Alpine instead and do not need this skill." Keep: strict mode, no `any`, schema validation at boundaries, promise discipline, state placement, feature-first layout. Remove: Next.js and Remix decision tree.

Green: `every_skill_is_a_SKILL_md`. Run `bash scripts/check.sh`. Commit: `Move skills to SKILL.md and state the Octopus stack as the default`.

### Task 1.4: Remove the throwaway banner and add context references

**Files:** Modify every file under `skills/`, `loops/`, `subagents/` that carries the banner.

Replace the banner with one line: "Calibrate every judgement call to the project context block in the instruction files. Where it is missing, ask before assuming anything about who depends on this code." Green: `no_file_claims_the_project_is_a_throwaway`. Commit: `Replace the throwaway banner with a project-context reference`.

### Task 1.5: Lighter plan skill

**Files:** Rewrite `skills/plan/SKILL.md`

Keep: the header block (goal, architecture, stack), the file map, one task per commit with files listed, failing test named before implementation, self-review (spec coverage, placeholder scan, name consistency), save to `docs/plans/YYYY-MM-DD-<name>.md`. Drop: the announce line, 2-5 minute steps, mandatory code for every step (code only where the shape is not obvious from the description), "subagent-driven vs inline" handoff, references to brainstorming and executing-plans. Commit: `Simplify the plan skill to commit-sized tasks`.

### Task 1.6: Split the rules into conduct and defaults

**Files:**
- Create: `content/conduct/conduct.md`, `content/conduct/secrets.md`
- Create: `content/defaults/{tdd,git,observability,migrations,api,standards,quality-gates}.md`
- Delete: `rules/*.md` (after `scripts/` and `.claude/CLAUDE.md` point at the new paths)
- Modify: `scripts/init-repo.sh`, `scripts/sync-codex-rules.sh`, `scripts/sync-cursor-rules.sh`, `scripts/install.sh`, `scripts/uninstall.sh`, `.claude/CLAUDE.md`, `AGENTS.md`

`conduct.md`, under forty lines, carries CONTRIBUTING's golden rules in machine-loadable form: no externally visible action (push, merge, close, comment, message, delete) without explicit per-action permission; never merge; never force-push the default branch; hooks and checks run normally, never bypassed or weakened, a blocked or waived check is not a pass; report outcomes faithfully. `secrets.md` stays as is.

Defaults carry the adjustments decided above: `git.md` says "the default branch" and references `git rev-parse --abbrev-ref origin/HEAD`; `standards.md` loses Docker, workflow naming, settings naming, tests layout and the "users, teams, goals, tasks" example, and keeps "backend owns the truth, organise by domain, frontend orchestrates"; `api.md` holds the API section; `quality-gates.md` holds lint, format, types, tests, dependency scan before merge, and `make check` / `make check-fast` as the named commands. Every default opens with "Default for OEES projects. A project opts out in its manifest."

Scripts keep working by reading `content/conduct` and `content/defaults` together until Phase 2 replaces them. Commit: `Split rules into always-on conduct and opt-out defaults`.

### Task 1.7: Genericise the subagents and split core from extended

**Files:**
- Move: `subagents/{test-writer,functional-reviewer,engineering-reviewer,security-reviewer}.md` to `content/subagents/core/`
- Rename and move: `python-implementer.md` to `core/implementer.md`, `de-slopper.md` to `core/simplifier.md`
- Move: `migration-reviewer, infra-implementer, infra-reviewer, ui-reviewer, documentation-writer, docs-verifier` to `content/subagents/extended/`
- Move: `subagents/skills/reviewing/SKILL.md` to `skills/reviewing/SKILL.md`
- Modify: `subagents/README.md` to `content/subagents/README.md`

Edits in every definition: replace named commands with "the fast checks named in the project context"; replace tool names with the category ("the migration linter, if the project has one"); replace "the tech lead's review" with "human review"; `ui-reviewer` describes both the server-rendered pattern and the SPA pattern without naming HTMX; the docs pair refers to "the project's decision labels, if it has them". `implementer.md` is language-agnostic: it reads the kit skills preloaded for it. `engineering-reviewer` and `simplifier` preload `code-review` through `skills:` frontmatter and lose their duplicated maintainability text, so the three overlapping texts become one source. `frontend-implementer` merges into `implementer` (one implementer, paths decide the surface). Green: `subagents_contain_no_project_vocabulary`, `no_dangling_skill_references`. Commit: `Make the subagents generic and split core from extended`.

### Task 1.8: Fix the remaining doc drift

**Files:** Modify `CONTRIBUTING.md`, `README.md`, `.claude/CLAUDE.md`

CONTRIBUTING: settings split to `base/local/test/production`, install snippet includes `AGENTS.md`, golden rules point at `conduct.md`, the repo table gains a "kits" column, the "repo always wins" sentence becomes "the project context and manifest always win". This repo's own CLAUDE.md imports conduct plus all defaults. Commit: `Align CONTRIBUTING and README with the new tiers`.

---

## Phase 2: The installer

### Task 2.1: Package skeleton and manifest round-trip

**Files:**
- Modify: `pyproject.toml` (project `oees-agents`, script entry `oees-agents = "oees_agents.cli:app"`, deps typer, questionary, tomli-w; dev deps pytest, ruff, mypy)
- Create: `src/oees_agents/__init__.py`, `manifest.py`
- Create: `tests/test_manifest.py`
- Create: `Makefile` with `check` and `check-fast`

Tests first: a manifest written then read is equal; unknown keys fail validation with the key named; `rules.defaults` may be empty; `extras.subagents` only accepts `none|core|extended`; `blast_radius` only accepts the three values. Commit: `Add the oees-agents package with a validated manifest`.

### Task 2.2: Content loader

**Files:** Create `src/oees_agents/content.py`, `tests/test_content.py`

Loads tiers, skills, kits, subagents and loops from `content/` and `skills/` with frontmatter parsed. Tests: every expected tier and skill is found; a skill directory without SKILL.md raises; the content lint tests from Task 1.1 move here and run against the loader. Commit: `Load canonical content with parsed frontmatter`.

### Task 2.3: Renderer and Claude Code target

**Files:** Create `src/oees_agents/render.py`, `targets/claude.py`, `content/blocks/project-context.md.j2`, `tests/test_render_claude.py`

Given a manifest, produce a mapping of relative path to bytes. For Claude: `.claude/CLAUDE.md` with the managed context block followed by `@rules/` imports for conduct plus the enabled defaults; `.claude/rules/`, `.claude/skills/` (commands' skills, pattern skills, enabled kits, `reviewing` when subagents are on), `.claude/commands/`, `.claude/agents/` (core or extended), `.claude/loops/` (selected), `.claude/settings.json` generated: allowlist from kits (pytest, ruff, mypy, uv for Python kits; npm, tsc, eslint for TS), deny list as decided, no hooks.

Tests: an opted-out default produces no file and no import; the context block appears exactly once after two renders; a CLAUDE.md with project text outside the managed block keeps that text byte for byte; settings.json has no `rm` deny and no hook; `subagents = "none"` produces no `.claude/agents/`. Commit: `Render the Claude Code target from a manifest`.

### Task 2.4: Cursor and Codex targets

**Files:** Create `targets/cursor.py`, `targets/codex.py`, `tests/test_render_cursor.py`, `tests/test_render_codex.py`

Cursor: `00-project-context.mdc` (alwaysApply), one `.mdc` per conduct and enabled default (alwaysApply), pattern skills and kits as glob-attached, commands' skills as agent-requested. Codex: the managed `AGENTS.md` block with the context block first, then conduct and enabled defaults. Port every behaviour `scripts/check.sh` guards today into tests: local text outside the block preserved, idempotent, malformed or duplicate markers refused without changes, symlink refused, CRLF preserved, 32 KiB warning. Commit: `Render the Cursor and Codex targets`.

### Task 2.5: Writing to disk and `update`

**Files:** Create `src/oees_agents/writer.py`, `tests/test_writer.py`

Writes only files the renderer owns, records them in `.oees-agents.lock` (path and hash), and on `update` removes files it wrote before that the new render no longer produces, so disabling a kit cleans up. Never touches a file whose hash differs from the lock without `--force`, and lists them. Tests cover each sentence above. Commit: `Write rendered files with an ownership lock`.

### Task 2.6: Interactive `init` and flags

**Files:** Create `src/oees_agents/questions.py`, `cli.py`, `tests/test_cli.py`

`oees-agents init` asks, in order: targets (multi-select, defaults from what exists in the repo: `.cursor/` present selects Cursor, and so on), project name (default: directory name), one-paragraph description, users, blast radius, default branch (default: detected), check commands (default: `make check` / `make check-fast`), kits (multi-select, with detection hints: `manage.py` suggests django-drf, `fastapi` in a dependency manifest suggests fastapi, `hx-` in templates suggests htmx-alpine), defaults to keep (multi-select, all on), subagents (none/core/extended), loops. Every question has a flag (`--target`, `--kit`, `--no-default tdd`, `--description "..."`, `--yes`) so CI and scripts can run it non-interactively. `oees-agents update` re-renders from the manifest, `--ref` picks the content version. `oees-agents check` exits non-zero when generated files are stale. `oees-agents list` prints the available kits, defaults and extras with one line each. Tests use typer's runner with answers piped in. Commit: `Add init, update, check and list commands`.

### Task 2.7: Legacy migration

**Files:** Create `src/oees_agents/legacy.py`, `tests/test_legacy.py`

Detects a pre-manifest install (`.claude/rules/*.md` copied from this repo, `AGENTS.md` with the old markers). Builds a manifest from what is present (which rules exist, Cursor present or not), asks only the context questions, removes the old files it can prove came from this repo (hash matches a known historical version), keeps everything else and lists it. Tests: a fixture tree from the current `init-repo.sh` output migrates to a manifest with all defaults on and no project context; local lines in the old CLAUDE.md survive. Commit: `Migrate pre-manifest installs to a manifest`.

### Task 2.8: Replace the shell scripts and CI

**Files:**
- Delete: `scripts/bootstrap.sh`, `init-repo.sh`, `install.sh`, `uninstall.sh`, `sync-cursor-rules.sh`, `sync-codex-rules.sh`, `check.sh`
- Delete: `.cursor/rules/` (generated at install from now on)
- Create: `scripts/bootstrap.sh` (new, ten lines: install uv if missing, then `uvx --from git+https://github.com/oees/agents@<latest tag> oees-agents init "$@"`)
- Modify: `.github/workflows/tooling-ci.yml` to `uv sync`, `make check`
- Modify: `.claude/settings.json` for this repo only (no sync hook)

This repo dogfoods itself: `make check` runs ruff, mypy, pytest, and `oees-agents check .` against its own manifest. Commit: `Replace the shell installer with the CLI and run it in CI`.

### Task 2.9: npm shim

**Files:** Create `npm/package.json` (`@oees/agents`, bin `oees-agents`), `npm/bin/oees-agents.js`, `npm/README.md`

The bin looks for `uv` on PATH; if absent it prints the one-line uv install command and exits 1 (it never installs silently); otherwise it execs `uvx --from git+https://github.com/oees/agents@<pinned tag> oees-agents` with the same arguments. The pinned tag is updated by the release workflow. No logic lives in the shim. Test: a Node test that runs the bin with a fake `uv` on PATH and asserts the arguments. Commit: `Add an npm shim that runs the Python CLI`.

---

## Phase 3: Stack kits

Each kit is `content/kits/<name>/SKILL.md` plus `templates/`. The SKILL.md states the layout, settings, logging, errors, tests, Makefile targets, container and deploy path for that stack, in that order, and says which template to copy for each. Templates are real files a project can copy unchanged: `Makefile`, `Dockerfile`, `compose.yml`, `.github/workflows/ci.yml`, a health endpoint, a logging config, `.env.example`. A test per kit renders a manifest with only that kit and asserts the skill and templates land under `.claude/skills/<kit>/`.

### Task 3.1: `django-drf`

Django 5 + DRF, per-app `tests/`, settings `base/local/test/production`, Celery for queues, Postgres (TimescaleDB where telemetry), structured JSON logging with request and task ids, `/api/v1/` with pagination and an error envelope, multi-tenancy note (tenant scoping at the queryset level, where it applies), migrations rule reference, pre-deploy migration job, DigitalOcean App Platform spec. Commit: `Add the django-drf kit`.

### Task 3.2: `fastapi`

FastAPI, SQLAlchemy 2 (async where the service is I/O bound), Alembic, uv, top-level `tests/` mirroring the package, Pydantic settings split by environment, HTTPX with retries for outbound calls, structured logging, health endpoint, DigitalOcean App Platform spec. Commit: `Add the fastapi kit`.

### Task 3.3: `htmx-alpine`

Server-rendered UI on Django: one URL per screen, partials named after the element they replace, triggering controls disabled while a request runs, validation re-renders the form with errors, strict CSP with no inline scripts (Alpine's CSP build), design tokens, translations, accessibility checklist, template linting. This is where the UI reviewer's former specifics live. Commit: `Add the htmx-alpine kit`.

---

## Phase 4: Docs, release, rollout

### Task 4.1: README and CONTRIBUTING

README: install with `uvx`, `npx` and the bootstrap one-liner; what `init` asks; the manifest explained; what each tier and kit is for. CONTRIBUTING becomes the "why" document: the philosophy (fair, clean, simple energy; the customer is the point; backend owns the truth; small reviewable changes; visible tracked debt) and the rule, kit and subagent tables generated from `content/` by `make docs`, checked in CI so they cannot drift. Commit: `Rewrite README and CONTRIBUTING around the installer and tiers`.

### Task 4.2: Release workflow

`.github/workflows/release.yml`: on a `v*` tag, run `make check`, update the npm shim's pinned tag and publish `@oees/agents`. Tag `v1.0.0` once Tasks 1 to 4.1 are merged. Commit: `Add a tag-driven release workflow`.

### Task 4.3: Pilot and rollout

Run `oees-agents init` on one repo per kit (hermes for fastapi, franklin for django-drf plus htmx-alpine), commit the manifest and generated files there, work with them for a week, fold the feedback back into the kits, then migrate the rest with `oees-agents init` (legacy migration path). Record per-repo opt-outs in each manifest with a one-line reason comment.

---

## Self-review

- **Coverage of the six asks:** opt-in installer (Phase 2), no throwaway premise (Tasks 1.4, 2.3), generic subagents (1.7), SKILL.md and stronger language (1.3), unified conventions (decisions table, 1.6, 1.8), concrete proposals (decisions table and defaults list).
- **Placeholders:** none; every task names its files, its failing tests and its commit.
- **Name consistency:** `make check` / `make check-fast`, `.oees-agents.toml`, `content/`, `core` / `extended`, `blast_radius` are used identically throughout.
- **Ordering:** Phase 1 keeps the bash scripts working at every commit; Phase 2 deletes them only once the CLI covers every behaviour `check.sh` tested; kits need the renderer, so Phase 3 follows Phase 2; the pilot needs a tag.
