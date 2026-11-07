# agents

Shared AI-agent configuration for Octopus Energy España (OEES) projects, for Claude Code, Cursor and Codex. It gives a project rules, skills, slash commands, subagents, scheduled-agent loops and stack kits, and the project chooses which of them it takes. The Octopus way is the default: a small conduct core is always on, the default rules are on unless a project opts out of them, and kits and extras are opt-in. A project's choices live in one committed manifest, and the `oees-agents` CLI generates every tool's files from it.

## Install

Run one of these from the root of the project. All three run the same CLI; pick whichever suits your machine.

**With uv** (use the latest release tag; `v1.0.0` is the first):

```bash
uvx --from git+https://github.com/oees/agents@v1.0.0 oees-agents init
```

This needs [uv](https://docs.astral.sh/uv/).

**With npm:**

```bash
npx @oees/agents init
```

`@oees/agents` is a thin shim: it runs the same CLI through `uvx`, pinned to the tag the shim was published with. It never installs uv for you. If uv is missing it prints the uv install command and exits with status 1.

**With nothing installed:**

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/oees/agents/main/scripts/bootstrap.sh)
```

The bootstrap script installs uv if it is missing, then runs `init` from the latest release tag (set `OEES_AGENTS_REF` to pick another tag or branch). Arguments after the script go to `init`. Run it as above for the interactive questions: piped into bash, the script's stdin is the pipe, so `init` cannot read your answers. Piping works only for a run that asks nothing:

```bash
curl -fsSL https://raw.githubusercontent.com/oees/agents/main/scripts/bootstrap.sh | bash -s -- --yes \
  --description "..." --users "..."
```

To read the script before running it:

```bash
curl -fsSL https://raw.githubusercontent.com/oees/agents/main/scripts/bootstrap.sh -o bootstrap.sh
less bootstrap.sh
bash bootstrap.sh
rm bootstrap.sh
```

Then commit the result. Add only the targets you picked:

```bash
git add .oees-agents.toml .oees-agents.lock AGENTS.md .claude/ .cursor/
git commit -m "Add OEES agent configuration"
```

Once committed, everyone on the project gets the same configuration. The rest of this README writes `oees-agents <command>`; run it through the entry point you used, for example `uvx --from git+https://github.com/oees/agents@<tag> oees-agents update` or `npx @oees/agents update`.

## What `init` asks

`init` asks once and records the answers in `.oees-agents.toml`. It refuses to run where a manifest already exists; use `update` there. In order:

| # | Question | Default | Flag |
|---|---|---|---|
| 1 | Targets: `claude`, `cursor`, `codex` (multi-select) | Detected: `.claude/` or `CLAUDE.md` selects Claude Code, `.cursor/` selects Cursor, `AGENTS.md` selects Codex; all three when none is found | `--target` (repeat) |
| 2 | Project name | The directory name | `--name` |
| 3 | One-paragraph description | none | `--description` |
| 4 | Who uses it | none | `--users` |
| 5 | Blast radius: `internal`, `customer-facing` or `regulated` | `internal` | `--blast-radius` |
| 6 | Default branch | `origin/HEAD`, else `main` | `--default-branch` |
| 7 | Full and fast check commands | `make check` / `make check-fast` | `--check`, `--check-fast` |
| 8 | Kits (multi-select) | Suggested from the repo: `manage.py` suggests `django-drf`, `fastapi` in `pyproject.toml` or `requirements*.txt` suggests `fastapi`, `hx-` in a `templates/**/*.html` file suggests `htmx-alpine` | `--kit` (repeat), `--no-kits` |
| 9 | Defaults to keep (multi-select) | All of them | `--no-default <name>` (repeat) |
| 10 | Subagents: `none`, `core` or `extended` | `core` | `--subagents` |
| 11 | Loops (multi-select) | None | `--loop` (repeat) |

The slash commands are not a question: they install unless you pass `--no-commands`. `--yes` (`-y`) asks nothing and takes each flag, else the default; the description and users have no default, so `--yes` needs `--description` and `--users`. `init` also takes `--force`, `--ref` and `--content-dir`, described under [Updating](#updating), and the project root as an optional argument (default `.`).

```bash
uvx --from git+https://github.com/oees/agents@v1.0.0 oees-agents init --yes \
  --target claude --target codex \
  --description "Middleware that relays meter readings from partner APIs to Kraken." \
  --users "OEES operations, partner integrations" \
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

| Field | Meaning |
|---|---|
| `version` | Manifest format version. Currently `1`. |
| `source` | The content version the generated files came from: `v<version>` of the CLI that rendered them, the `--ref` it was given, or `local` for `--content-dir`. `update` rewrites this line and nothing else. |
| `targets` | Which tools to generate files for: any of `claude`, `cursor`, `codex`. |
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
| `extras.loops` | The loop templates to install. Empty by default. |

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
**octohub**: B2B multi-tenant platform where partners and vendors sell and install energy products.
Used by: external partners, vendors, OEES operations. Blast radius: customer-facing.
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
| `secrets` | Never commit secrets; use env vars and secret managers |
<!-- END GENERATED: conduct -->

### Defaults (on unless the project opts out)

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
| `reviewing` | The shared protocol for reviewer subagents and the docs verifier — inputs, read-only working, severity levels and the findings report. Use whenever reviewing a change. |
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

### Loops (`extras.loops`, opt-in)

Templates for unsupervised cloud agents that run on a schedule. Fill in the per-repo config block at the top and leave the rest untouched.

<!-- BEGIN GENERATED: loops -->
| Loop | What it does |
|---|---|
| `tier-0-daily-health-scan` | Tier-0 Daily Health Scan — Automation Instructions |
| `tier-1-increase-test-coverage` | Tier-1 Weekly Test-Coverage Filler — Automation Instructions |
| `tier-2-behavioural-improvements` | Tier-2 Behavioral-Change Fixer — Automation Instructions |
<!-- END GENERATED: loops -->

### Generated Claude Code settings

`.claude/settings.json` is generated from the manifest:

- **Allow**: read-only and local Git commands (`git status`, `diff`, `log`, `show`, `branch`, `add`, `commit`, `stash`, `rebase`, `fetch`), basic file commands (`ls`, `find`, `grep`, `cat`, `head`, `tail`, `wc`, `mkdir`, `mv`, `cp`, `touch`), the project's `check` and `check_fast` commands, and the Python toolchain (`uv`, `pytest`, `ruff`, `mypy`) when a kit needs it. All three current kits do.
- **Deny**: `git push`, `git push --force`, `git reset --hard`, `git rebase -i`, `git rebase --interactive` and `git filter-branch`. `rm` is not denied.
- **Hooks**: none.

A `settings.json` the project already had and the CLI did not write is left alone and reported; `--force` replaces it.

### Generated files per target

```
.oees-agents.toml             the manifest
.oees-agents.lock             what the CLI owns, with hashes

claude:
.claude/
  CLAUDE.md                   managed block at the top: context, then @rules/ imports
  rules/                      conduct and kept defaults
  skills/                     every skill, enabled kits with templates/; reviewing only with subagents
  commands/                   slash commands, unless extras.commands = false
  agents/                     core, or core and extended, subagents
  loops/                      selected loop templates
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

## Updating

```bash
oees-agents update
oees-agents update --ref v1.1.0
oees-agents update --ref main
```

`update` re-renders every generated file from the manifest. The content comes from the CLI you run: `uvx --from git+https://github.com/oees/agents@v1.1.0 oees-agents update` renders `v1.1.0`, and `npx @oees/agents update` renders the tag that shim was published with. `--ref <tag or branch>` instead clones that version of this repository (it needs `git`), and `--content-dir <path>` renders from a local checkout. `update` then pins the manifest's `source` to what it rendered, rewriting that one line only, so comments in the manifest survive.

Files the CLI wrote before that the new render no longer produces are removed, so disabling a kit cleans up after it. A file or managed block whose hash differs from the lock (someone edited it), or a file the CLI did not write, is never overwritten without `--force`; `update` lists it and leaves it alone. Symlinks and malformed markers are refused even with `--force`. Review the diff and commit it.

## Checking

```bash
oees-agents check
```

`check` exits non-zero when a generated file or block is missing, stale, edited by hand or no longer rendered, and lists each one. It renders the same way `update` does, so run it at the version the manifest pins (it prints a note when they differ). Add it to the project's CI so the manifest and the files cannot drift apart:

```bash
uvx --from git+https://github.com/oees/agents@v1.0.0 oees-agents check
```

## Opting out of a default

Remove the rule from `rules.defaults`, put a one-line `# <name>: <reason>` comment on the line above, then run `oees-agents update`. [docs/rollout.md](docs/rollout.md#opt-out-convention) has the full convention.

```toml
[rules]
# migrations: this service has no database of its own
defaults = ["tdd", "git", "observability", "api", "standards", "quality-gates"]
```

At install, `--no-default migrations` does the same. Conduct (`conduct`, `secrets`, `data-protection`) cannot be opted out.

Kits and extras work the same way: remove the kit from `kits.enabled`, set `commands = false`, set `subagents = "none"` or drop a loop from `loops`, add the reason above it, and run `update`. The files that are no longer produced are removed. `update` never rewrites the manifest beyond its `source` line, so the reason comments stay.

## Existing installs

If the project was set up with the old bootstrap script, run `oees-agents init` as for a new install. It detects the old install and takes the targets, kept defaults, loops and commands from what is present; kits and subagents start off (pass `--kit` or `--subagents` to turn them on), so it asks only the project-context questions. It removes the old files whose bytes match a version this repository once shipped at that path, keeps the ones you edited and lists them so you can decide. In the old `.claude/CLAUDE.md`, only the `@rules/` imports are removed; every other line survives.

## Codex notes

Codex [reads `AGENTS.md` at startup](https://learn.chatgpt.com/docs/agent-configuration/agents-md). The CLI writes the project context, conduct and the kept defaults in full into a managed block, so loading them does not depend on following links or on Claude's `@imports`. Codex gets the rules only; skills, commands, subagents and loops are for Claude Code (and skills for Cursor).

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
loops/             loop templates
npm/               the @oees/agents shim and its test
scripts/           bootstrap.sh, and generate_legacy_hashes.py for the legacy migration
tests/             pytest, one file per module plus content lint tests
hatch_build.py     bundles content/, skills/, commands/ and loops/ into the wheel
```

```bash
uv sync
make check-fast   # lint, format, types and the fast tests, while working
make check        # the contributor gate: ruff, format, mypy, every test, the npm shim test,
                  # and oees-agents check against this repo's own manifest
make docs         # regenerate the tables in README.md and CONTRIBUTING.md
```

This repository installs itself for Codex: `.oees-agents.toml`, `.oees-agents.lock` and the managed block in `AGENTS.md`. After changing `content/`, `skills/`, `commands/` or `loops/`, run `uv run --frozen oees-agents update . --content-dir .` and `make docs`; `make check` fails until both are current. CI (`tooling-ci.yml`) runs `make check`. Releases are tag-driven: pushing a `v*` tag that matches the version in `pyproject.toml` runs `make check` and publishes the npm shim pinned to that tag.

[CONTRIBUTING.md](CONTRIBUTING.md) explains why the rules are what they are, and how to add a rule, kit or subagent.
