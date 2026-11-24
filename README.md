# agents

Shared AI-agent configuration for Octopus Energy España (OEES) projects, for Claude Code, Cursor and Codex. It gives a project rules, skills, slash commands, subagents and stack kits, and the project chooses which of them it takes. The Octopus way is the default: a small conduct core is always on, the default rules are on unless a project opts out of them, and kits and extras are opt-in. A project's choices live in one committed manifest, and the `oees-agents` CLI generates every tool's files from it.

## Install

The only way to install is `uvx`. You need [uv](https://docs.astral.sh/uv/getting-started/installation/) and `git`. There is no release yet, so install from the `main` branch. Run this command from the root of the project:

```bash
uvx --from git+https://github.com/oees/agents@main oees-agents init
```

`uvx` runs the CLI in a temporary environment. It installs nothing in the project and nothing globally.

**After the first release:** each release is a `v*` tag. Replace `@main` with the tag, for example `@v1.0.0`, so that every machine renders the same content.

### This project or the whole machine

`init` first asks where to install. `--project` or `--machine` answers the question.

- **This project** (the default): the files go into the project and you commit them, so everyone on the project gets the same configuration. This is the only scope with a project context and Cursor rules.
- **The whole machine**: the files go into your home directory, where each tool reads instructions for every project on the machine. Nothing is committed anywhere. Use it for your own repositories, or for repositories that have no install of their own.

```bash
uvx --from git+https://github.com/oees/agents@main oees-agents init --machine
```

| Tool | Machine install writes |
|---|---|
| Claude Code | `~/.claude/` (or `$CLAUDE_CONFIG_DIR`): the managed block at the top of `CLAUDE.md`, `rules/oees-agents/`, `skills/`, `commands/`, `agents/` and `settings.json` |
| Codex | `~/.codex/` (or `$CODEX_HOME`): the rules in `oees-agents/rules.md`, a session hook in `oees-agents/session-start.sh` and `hooks.json`. Your `AGENTS.md` there is not changed. |
| Cursor | nothing: Cursor reads rule files only from a project. Install it per project. |

The manifest and the lock go to `~/.oees-agents.toml` and `~/.oees-agents.lock`. A machine install asks no project question (name, description, users, blast radius, branch, checks), so it has no project context block. Your own text in `~/.claude/CLAUDE.md` outside the managed block stays, and so does a `~/.claude/settings.json` or `~/.codex/hooks.json` that you already had. `$CLAUDE_CONFIG_DIR` and `$CODEX_HOME` must point inside your home directory.

The machine install applies to every project, unless the project has its own install. Each tool handles this differently:

- **Claude Code rules**: the project install's `.claude/settings.json` tells Claude Code to skip the machine rules, with `"claudeMdExcludes": ["**/rules/oees-agents/**"]`. So the project's rules apply, not both. If the project keeps its own `settings.json`, add that line to it yourself; `init` prints it.
- **Claude Code skills and subagents**: Claude Code uses the machine skill when the machine and the project have a skill with the same name, and the project subagent when both have a subagent with the same name. No setting changes this. Keep both installs on the same version.
- **Codex**: Codex loads `~/.codex/AGENTS.md` in every project and has no setting to skip it, so the machine install does not use that file. A session hook gives Codex the rules instead. At each new session, `/clear` or compaction, the hook looks for a `.oees-agents.toml` from the working directory up to the Git root. If it finds a project install for Codex, it prints nothing, so the project's `AGENTS.md` applies. Otherwise it prints the machine rules.
  - Codex runs the hook only after you approve it. Start Codex and run `/hooks`. Until then, Codex does not load the machine rules. An `update` that changes only the rules needs no new approval.
  - If you already have a `~/.codex/hooks.json`, the CLI keeps it and prints the hook for you to add.
  - The hook sets `"additionalContextLimit": 0`. Without it, Codex moves hook output above 2,500 tokens to a file and shows only a preview.

Then commit the result. Add only the targets you picked:

```bash
git add .oees-agents.toml .oees-agents.lock AGENTS.md .claude/ .cursor/
git commit -m "Add OEES agent configuration"
```

When you commit these files, everyone on the project gets the same configuration. The rest of this README writes `oees-agents <command>`. Run it through the entry point you used, for example `uvx --from git+https://github.com/oees/agents@main oees-agents update`.

## What `init` asks

`init` asks once and records the answers in `.oees-agents.toml`. It refuses to run where a manifest already exists; use `update` there. In order:

| # | Question | Default | Flag |
|---|---|---|---|
| 1 | Install for: `project` or `machine` | `project` | `--project`, `--machine` |
| 2 | Targets: `claude`, `cursor`, `codex` (multi-select; no `cursor` for the machine) | Detected: `.claude/` or `CLAUDE.md` selects Claude Code, `.cursor/` selects Cursor, `AGENTS.md` selects Codex; all three when none is found. For the machine: `~/.claude/` and `~/.codex/`, else both | `--target` (repeat) |
| 3 | Project name (not for the machine) | The directory name | `--name` |
| 4 | One-paragraph description (not for the machine) | none | `--description` |
| 5 | Who uses it (not for the machine) | none | `--users` |
| 6 | Blast radius: `internal`, `customer-facing` or `regulated` (not for the machine) | `internal` | `--blast-radius` |
| 7 | Default branch (not for the machine) | `origin/HEAD`, else `main` | `--default-branch` |
| 8 | Full and fast check commands (not for the machine) | `make check` / `make check-fast` | `--check`, `--check-fast` |
| 9 | Kits (multi-select) | Suggested from the repo: `manage.py` suggests `django-drf`, `fastapi` in `pyproject.toml` or `requirements*.txt` suggests `fastapi`, `hx-` in a `templates/**/*.html` file suggests `htmx-alpine` | `--kit` (repeat), `--no-kits` |
| 10 | Defaults to keep (multi-select) | All of them | `--no-default <name>` (repeat) |
| 11 | Subagents: `none`, `core` or `extended` | `core` | `--subagents` |

The slash commands are not a question: they install unless you pass `--no-commands`. `--yes` (`-y`) asks nothing and takes each flag, else the default; the description and users have no default, so a project install with `--yes` needs `--description` and `--users`. A machine install with `--yes` needs neither, and refuses the project flags. `init` also takes `--force`, `--ref` and `--content-dir`, described under [Updating](#updating), and the project root as an optional argument (default `.`).

```bash
uvx --from git+https://github.com/oees/agents@main oees-agents init --yes \
  --target claude --target codex \
  --description "Service that collects meter readings from external APIs." \
  --users "OEES operations" \
  --blast-radius customer-facing \
  --kit fastapi \
  --no-default migrations
```

## The manifest

`.oees-agents.toml` sits at the project root, is committed, and is the single source of truth for what the project takes. Every later run reads it. Re-runs never re-add something the project removed. Unknown keys and values outside the allowed choices fail validation, and the error names the key.

```toml
version = 1
source = "v1.0.0"
targets = ["claude", "cursor", "codex"]

[project]
name = "example-portal"
description = "Web portal where customers manage their energy contracts."
users = "OEES customers and the support team"
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
```

| Field | Meaning |
|---|---|
| `version` | Manifest format version. Currently `1`. |
| `source` | The content version the generated files came from: `v<version>` of the CLI that rendered them, the `--ref` it was given, or `local` for `--content-dir`. An install from `main` records the version in `pyproject.toml` (now `v0.1.0`), which is not a tag yet. `update` rewrites this line and nothing else. |
| `scope` | `machine` for a machine install. A project manifest leaves it out (it means `project`). |
| `targets` | Which tools to generate files for: any of `claude`, `cursor`, `codex`. A machine install takes only `claude` and `codex`. |
| `project.name` | The project's name, as agents should refer to it. |
| `project.description` | One paragraph on what the project is and does. |
| `project.users` | Who depends on it. |
| `project.blast_radius` | How far a mistake reaches (see below). |
| `project.default_branch` | The branch agents rebase onto and never force-push. Detected at install, never assumed. |
| `project.check` | The full check, run before handing work over. |
| `project.check_fast` | The fast check (lint, format, types, targeted tests), run while working. |
| `rules.defaults` | The default rules this project keeps. May be empty. Conduct is not listed here because it is always on. |
| `kits.enabled` | The stack kits this project uses. |
| `extras.commands` | Install the slash commands (`.claude/commands/`). The skills behind them install either way. |
| `extras.subagents` | `none`, `core` or `extended` (core plus the extended set). |

`blast_radius` takes one of three values, and agents calibrate their caution to it:

| Value | Meaning | How agents calibrate |
|---|---|---|
| `internal` | Used by OEES staff only. | Still production code that people depend on; never a throwaway. |
| `customer-facing` | External customers or partners use it directly. | Treat behaviour changes, compatibility and data handling as visible to people outside OEES. |
| `regulated` | Subject to regulatory or contractual obligations. | Highest care; ask before anything that could affect those obligations. |

`.oees-agents.lock` records the sha256 of every file the CLI wrote and of every managed block it keeps inside a file you also edit. Commit it alongside the manifest; `update` and `check` use it to know what the CLI owns and whether someone edited it since.

### The project-context block

The `[project]` answers become a managed block that tells every agent what it is working on:

```markdown
<!-- BEGIN OEES PROJECT CONTEXT -->
## Project context
**example-portal**: Web portal where customers manage their energy contracts.
Used by: OEES customers and the support team. Blast radius: customer-facing.
Stack: django-drf, htmx-alpine. Default branch: main.
Checks: `make check-fast` while working, `make check` before handing over.
Calibrate every judgement call to this context. Never assume the code is a throwaway.
<!-- END OEES PROJECT CONTEXT -->
```

It opens the managed block at the top of `.claude/CLAUDE.md` and the managed block at the bottom of `AGENTS.md`, and is `.cursor/rules/00-project-context.mdc` for Cursor. Those managed blocks sit between `<!-- BEGIN OEES SHARED RULES -->` and `<!-- END OEES SHARED RULES -->`; text you write outside them is preserved byte for byte, with its line endings.

## What you get

`oees-agents list` prints the same catalogue for the content version you run. The tables below are generated from `content/` by `make docs`; do not edit them by hand.

### Conduct (always on)

<!-- BEGIN GENERATED: conduct -->
| Rule | What it covers |
|---|---|
| `conduct` | Always-on conduct — per-action permission for visible actions, never merge, hooks and checks never bypassed, faithful reporting |
| `data-protection` | Personal data stays out of logs, traces, errors, fixtures and prompts |
| `language` | Write English in ASD-STE100 Simplified Technical English and Spanish in plain language to UNE-ISO 24495-1 |
| `secrets` | Never commit secrets; use env vars and secret managers |
<!-- END GENERATED: conduct -->

### Defaults (on unless the project opts out)

<!-- BEGIN GENERATED: defaults -->
| Rule | What it covers |
|---|---|
| `api` | Versioned endpoints, consistent error envelopes, pagination, typed validation, token auth, generated docs |
| `git` | Every change reaches the default branch through a pull request, rebase-only merges, no merge commits, no squashing, commits that stand alone |
| `migrations` | Safe, backwards-compatible database schema migrations |
| `observability` | Structured logging, contextual errors, no silent exceptions |
| `quality-gates` | Lint, format, types, tests and dependency scan before merge, run through make check and make check-fast |
| `standards` | Backend owns the truth, organise by domain, frontend orchestrates, validated deploys |
| `tdd` | TDD: write failing tests before implementation, red-green-refactor |
<!-- END GENERATED: defaults -->

### Skills

<!-- BEGIN GENERATED: skills -->
| Skill | What it does |
|---|---|
| `code-review` | Run an extremely strict maintainability review for abstraction quality, giant files, and spaghetti-condition growth. Use for a code quality review or a code audit. |
| `commit` | Create a well-formed git commit following team standards — atomic scope, imperative subject ≤50 chars, body explaining what/why, 72-char line wrap. Use when the user asks to commit, wants to write a commit message, or invokes /commit. |
| `personal-data` | Keep personal data out of logs, traces, errors, analytics, exports, fixtures and model prompts. Use when adding logging or error handling, writing a serializer, export, webhook or analytics event, sending data to a third party or an LLM, creating test fixtures, or reviewing a change for PII exposure. |
| `plan` | Write an implementation plan from a spec or requirements before touching code — one commit-sized task at a time, each naming its files and its failing test. Use when given a spec, a feature brief, or a multi-step task to plan out. |
| `pr-tidy` | Prepare PRs for review by cleaning noisy history, improving PR descriptions, and adding reviewer guidance without changing code behavior. Use for "make this easy to review", "tidy this PR", "clean up commits", or "annotate the diff". |
| `python-patterns` | How OEES builds Python backends — Django + DRF or FastAPI, typed boundaries, domain exceptions, structured logging, settings per environment, imports at module top. Use when writing or reviewing Python code. |
| `reviewing` | The shared protocol that the reviewer subagents and the docs verifier preload — inputs, read-only working, severity levels and the findings report. Only those subagents use it; the main session asks a reviewer subagent for a review. |
| `shipped` | Summarize everything the user has personally authored and shipped across all local git repositories in a configurable time period. Use when the user asks "what did I ship?", "what have I worked on?", or wants a personal activity summary. |
| `test` | Write well-structured tests following TDD. Test design, mocking discipline, naming, and coverage decisions. Use when writing tests or reviewing test quality. |
| `typescript-patterns` | How OEES builds TypeScript frontends — React + TypeScript + Vite with TanStack Query, strict types, schema validation at boundaries, feature-first layout. Use when writing or reviewing TypeScript or React code. |
<!-- END GENERATED: skills -->

### Kits (opt-in)

<!-- BEGIN GENERATED: kits -->
| Kit | What it is for |
|---|---|
| `django-drf` | Use when building or changing a Django + Django REST Framework service, its Celery workers, or how it is tested, containerised and deployed to DigitalOcean App Platform. |
| `fastapi` | Use when building or changing a FastAPI service (API-only backends, middleware to external services, embeddable widget backends) in an OEES project. |
| `htmx-alpine` | Use when building or reviewing server-rendered Django screens with htmx and Alpine, covering templates, partials, forms, static assets, CSP, translations and accessibility. |
<!-- END GENERATED: kits -->

Each kit is a `SKILL.md` covering the stack's layout, settings, logging, errors, tests, Makefile targets, container and deploy path, plus `templates/` mirroring a project root, installed under `.claude/skills/<kit>/`. `django-drf` and `fastapi` ship a whole service skeleton to copy (Makefile with `check` and `check-fast`, Dockerfile, `compose.yml`, `.github/workflows/ci.yml` and `deploy.yml`, `.do/app.yaml`, `.env.example`, starter code and tests). `htmx-alpine` sits on a Django project and ships `make/htmx-alpine.mk`, which adds its template and asset checks to the existing `check` and `check-fast` targets, plus templates, static assets and settings fragments.

### Slash commands (`extras.commands`, on by default)

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

### Subagents (`extras.subagents`: `none`, `core` or `extended`)

`core` installs the core set; `extended` installs both sets; `none` installs no subagents.

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

### Generated Claude Code settings

`.claude/settings.json` is generated from the manifest:

- **Allow**: read-only and local Git commands (`git status`, `diff`, `log`, `show`, `branch`, `add`, `commit`, `stash`, `rebase`, `fetch`), basic file commands (`ls`, `grep`, `cat`, `head`, `tail`, `wc`, `mkdir`, `mv`, `cp`, `touch`), the project's `check` and `check_fast` commands, and the Python toolchain when a kit needs it: `uv sync`, `uv lock`, `uv run pytest`, `uv run ruff`, `uv run mypy`, `pytest`, `ruff` and `mypy`. All three current kits need it. Each command is allowed alone and with arguments, as `Bash(ls)` and `Bash(ls *)`, so `Bash(ls *)` does not also allow `lsof`.
- **Not allowed**: commands that run another program, such as `uv run <anything>`, `uvx`, `npx` and `find` (which can `-exec` or `-delete`). Claude Code asks first.
- **Deny**: `git push`, `git push --force`, `git reset --hard`, `git rebase -i`, `git rebase --interactive` and `git filter-branch`. `rm` is not denied.
- **Machine rules**: `claudeMdExcludes` skips the rules of a [machine install](#this-project-or-the-whole-machine), so this project's rules apply instead. It has no effect where there is no machine install. A machine install's own `settings.json` does not have it.
- **Hooks**: none.

If the project already has a `.claude/settings.json` that the CLI did not write, the CLI keeps it, does not manage it, and says so. `check` does not fail because of it. To take the generated file, delete yours or run `update --force`.

### Generated files per target

```
.oees-agents.toml             the manifest
.oees-agents.lock             what the CLI owns, with hashes

claude:
.claude/
  CLAUDE.md                   managed block at the top: context, then a note; Claude Code loads rules/ by itself
  rules/                      conduct and kept defaults
  skills/                     every skill, enabled kits with templates/; reviewing only with subagents
  commands/                   slash commands, unless extras.commands = false
  agents/                     core, or core and extended, subagents
  settings.json               as above

cursor:
.cursor/rules/
  00-project-context.mdc      context block, always applied
  <conduct and defaults>.mdc  always applied
  <pattern skills, kits>.mdc  attached by file glob
  <other skills>.mdc          agent-requested, by description

codex:
AGENTS.md                     managed block at the bottom: context, then conduct and kept defaults in full
```

A machine install writes the same Claude Code tree under `~/.claude/` (with the rules in `rules/oees-agents/`), the Codex rules and session hook under `~/.codex/`, and the manifest and lock into your home directory. See [This project or the whole machine](#this-project-or-the-whole-machine).

## Updating

```bash
oees-agents update
oees-agents update --ref main
oees-agents update --machine
```

`--machine` updates the machine install in your home directory, from any directory. Without it, `update` works on the project.

`update` re-renders every generated file from the manifest. The content comes from the CLI you run: `uvx --from git+https://github.com/oees/agents@main oees-agents update` renders `main`, and after a release, `uvx --from git+https://github.com/oees/agents@v1.1.0 oees-agents update` renders `v1.1.0`. `--ref <tag or branch>` instead clones that version of this repository (it needs `git`), and `--content-dir <path>` renders from a local checkout. `update` then pins the manifest's `source` to what it rendered, rewriting that one line only, so comments in the manifest survive.

Files the CLI wrote before that the new render no longer produces are removed, so disabling a kit cleans up after it. A file or managed block whose hash differs from the lock (someone edited it), or a file the CLI did not write, is never overwritten without `--force`; `update` lists it and leaves it alone. Symlinks and malformed markers are refused even with `--force`. Review the diff and commit it.

## Checking

```bash
oees-agents check
oees-agents check --machine
```

`check` exits non-zero when a generated file or block is missing, stale, edited by hand or no longer rendered, and lists each one. It renders the same way `update` does, so run it at the version the manifest pins (it prints a note when they differ). Add it to the project's CI so the manifest and the files cannot drift apart:

```bash
uvx --from git+https://github.com/oees/agents@main oees-agents check
```

When you install from `main`, run `check` from `main` too. When the project moves to a release tag, use that tag here.

## Opting out of a default

Remove the rule from `rules.defaults`, put a one-line `# <name>: <reason>` comment on the line above, then run `oees-agents update`. [docs/rollout.md](docs/rollout.md#opt-out-convention) has the full convention.

```toml
[rules]
# migrations: this service has no database of its own
defaults = ["tdd", "git", "observability", "api", "standards", "quality-gates"]
```

At install, `--no-default migrations` does the same. Conduct (`conduct`, `secrets`, `data-protection`, `language`) cannot be opted out.

Kits and extras work the same way: remove the kit from `kits.enabled`, set `commands = false` or set `subagents = "none"`, add the reason above it, and run `update`. The files that are no longer produced are removed. `update` never rewrites the manifest beyond its `source` line, so the reason comments stay.

## Existing installs

If the project was set up with the old install scripts, run `oees-agents init` as for a new install. It finds the old install by its proof: a file that this repository shipped, with its bytes unchanged, old `@rules/` imports in `.claude/CLAUDE.md`, or the old shared-rules marker in `AGENTS.md`. Your own files at the same paths are not proof. When it finds an old install, it takes the targets, kept defaults and commands from what is present; kits and subagents start off (pass `--kit` or `--subagents` to turn them on), so it asks only the project-context questions. It removes the old files whose bytes match a version this repository once shipped at that path, keeps the ones you edited and lists them so you can decide. In the old `.claude/CLAUDE.md`, only the `@rules/` imports are removed; every other line survives.

## Codex notes

Codex [reads `AGENTS.md` at startup](https://learn.chatgpt.com/docs/agent-configuration/agents-md). The CLI writes the project context, conduct and the kept defaults in full into a managed block, so loading them does not depend on following links or on Claude's `@imports`. Codex gets the rules only; skills, commands and subagents are for Claude Code (and skills for Cursor).

- Keep project commands and conventions outside the managed block. The CLI replaces only the block, preserves text around it and CRLF line endings, and refuses without changing anything if the markers are malformed or duplicated or if `AGENTS.md` is a symlink.
- An `AGENTS.override.md` in the same directory takes precedence over `AGENTS.md`. The CLI never touches it; check whether one exists.
- Codex's combined instruction size defaults to 32 KiB. The CLI warns when `AGENTS.md`, with its managed block, exceeds that. Keep an eye on other instruction files too.
- Restart running Codex sessions after `init` or `update`, then verify which instruction sources are active.

Three kinds of hook are easy to confuse:

- **Git hooks** run through ordinary Git commands in every client. Agents must fix failures and rerun the checks; a check blocked by the environment is reported, never bypassed or called a pass.
- **Claude Code tool hooks** live in `.claude/settings.json`. The generated settings configure none.
- **Codex lifecycle hooks** use [their own configuration and trust review](https://learn.chatgpt.com/docs/hooks). The CLI does not configure or trust them.

The rules guide the agent; the project's Git hooks and CI do the checking.

## Working on this repo

```
src/oees_agents/   the CLI: init, update, check, list; manifest, content loader, renderer,
                   targets/, writer and lock, legacy migration, content lint, docs tables
content/
  conduct/         always-on rules
  defaults/        opt-out rules
  kits/            SKILL.md plus templates/ per kit
  subagents/       core/ and extended/
  blocks/          the project-context block template
skills/            <name>/SKILL.md per skill
commands/          slash commands, each importing its skill
scripts/           generate_legacy_hashes.py for the legacy migration
tests/             pytest, one file per module plus content lint tests
hatch_build.py     bundles content/, skills/ and commands/ into the wheel
```

```bash
uv sync
make check-fast   # lint, format, types and the fast tests, while working
make check        # the contributor gate: ruff, format, mypy, every test,
                  # and oees-agents check against this repo's own manifest
make docs         # regenerate the tables in README.md and CONTRIBUTING.md
```

This repository installs itself for Codex: `.oees-agents.toml`, `.oees-agents.lock` and the managed block in `AGENTS.md`. After changing `content/`, `skills/` or `commands/`, run `uv run --frozen oees-agents update . --content-dir .` and `make docs`; `make check` fails until both are current. CI (`tooling-ci.yml`) runs `make check`. Releases are tag-driven: push a `v*` tag that matches the version in `pyproject.toml`. The release workflow checks the tag and runs `make check`; projects then install that tag with `uvx`.

[CONTRIBUTING.md](CONTRIBUTING.md) explains why the rules are what they are, and how to add a rule, kit or subagent.

## Licence

Proprietary. All rights reserved by Octopus Energy España. See [LICENSE](LICENSE): the repository is public, but that gives no right to use it outside Octopus Energy España.
