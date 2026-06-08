# agents

Shared agent configuration — rules, skills, and commands for Claude Code and Cursor.

## Install

### Global (your machine only)

```bash
bash scripts/install.sh
```

Symlinks commands into `~/.claude/commands/` and adds rules to `~/.claude/CLAUDE.md`. Active in every Claude Code session on this machine.

```bash
bash scripts/uninstall.sh  # reverses the above
```

### Per-repository (shareable with your team)

```bash
bash /path/to/agents/scripts/init-repo.sh [target-dir]
```

`target-dir` defaults to the current directory. The script copies rules, skills, and commands into `.claude/` inside the target repo. Commit `.claude/` and the whole team gets the tooling — no per-developer setup required.

Re-run the script to pull in rule or skill updates from this repo.

**What gets written:**

```
.claude/
  CLAUDE.md          # @imports for every rule
  rules/             # copies of all rules
  commands/          # copies of all commands
  skills/            # copies of all skills
  settings.json      # permissions and hooks (only written if not already present)
```

If `settings.json` already exists in the target repo it is left untouched. Review `/.claude/settings.json` in this repo and merge in any permissions or hooks you want.

## What you get

**Commands** (invoke with `/command-name` in Claude Code):

| Command | What it does |
|---|---|
| `/commit` | Well-formed git commit following team standards |
| `/code-review` | Strict maintainability review — abstraction quality, file size, spaghetti growth |
| `/plan` | Full implementation plan from a spec, with TDD tasks and exact file paths |
| `/pr-tidy` | Prepares a PR for review — cleans history, rewrites description, adds reviewer guidance |
| `/test` | Write well-structured tests following TDD — mocking discipline, naming, coverage decisions |
| `/shipped` | Summary of everything you've committed across all local repos in a time period |

**Rules** (always-on in every session):

| Rule | Enforces |
|---|---|
| `tdd` | Write failing tests before implementation, red-green-refactor |
| `observability` | Structured logging, contextual errors, no silent exceptions |
| `code-quality` | Lint, format, type checks, tests, and security scans before merge |
| `no-inline-imports` | Imports at top of module only |
| `standards` | Frontend, backend, deployment, and API design conventions |
| `git` | Branch hygiene, commit standards, no force-pushing main |
| `secrets` | No hardcoded credentials, use env vars and secret stores |
| `migrations` | Safe schema migrations — backwards-compatible, reversible, never drop data silently |

## Structure

```
rules/        canonical always-on rules (Claude Code via CLAUDE.md, Cursor via .cursor/rules/)
skills/       skill definitions referenced by commands
commands/     slash command entry points (@-importing their skill)
.claude/      Claude Code config (settings.json — shared permissions and hooks)
.cursor/      generated Cursor rules (do not edit directly)
scripts/      install.sh, uninstall.sh, init-repo.sh, sync-cursor-rules.sh
```

## Adding a rule

1. Create `rules/<name>.md` with a `description:` frontmatter field
2. Add `@rules/<name>.md` to `CLAUDE.md`
3. Run `bash scripts/sync-cursor-rules.sh` to generate the Cursor equivalent

## Adding a skill and command

1. Create `skills/<name>/<name>.md`
2. Create `commands/<name>.md` with frontmatter and `@skills/<name>/<name>.md`
3. Re-run `bash scripts/install.sh` (global) or `bash scripts/init-repo.sh` (per-repo) to pick up the new command

## Cursor

Cursor rules live in `.cursor/rules/` and are generated from `rules/` and `skills/python-patterns/`. The `PostToolUse` hook in `.claude/settings.json` auto-syncs them whenever a rule or the python-patterns skill is edited.
