# agents

Shared agent configuration — rules, skills, and commands for Claude Code and Cursor.

## Install

```bash
bash scripts/install.sh
```

Symlinks commands into `~/.claude/commands/` and adds rules to `~/.claude/CLAUDE.md` so everything is active globally in every Claude Code session.

```bash
bash scripts/uninstall.sh  # reverses the above
```

## What you get

**Commands** (invoke with `/command-name` in Claude Code):

| Command | What it does |
|---|---|
| `/commit` | Well-formed git commit following team standards |
| `/code-review` | Strict maintainability review — abstraction quality, file size, spaghetti growth |
| `/plan` | Full implementation plan from a spec, with TDD tasks and exact file paths |
| `/pr-tidy` | Prepares a PR for review — cleans history, rewrites description, adds reviewer guidance |
| `/shipped` | Summary of everything you've committed across all local repos in a time period |

**Rules** (always-on in every session):

| Rule | Enforces |
|---|---|
| `tdd` | Write failing tests before implementation, red-green-refactor |
| `observability` | Structured logging, contextual errors, no silent exceptions |
| `code-quality` | Lint, format, type checks, tests, and security scans before merge |
| `no-inline-imports` | Imports at top of module only |
| `standards` | Frontend, backend, deployment, and API design conventions |

## Structure

```
rules/        canonical always-on rules (Claude Code via CLAUDE.md, Cursor via .cursor/rules/)
skills/       skill definitions referenced by commands
commands/     slash command entry points (@-importing their skill)
.claude/      Claude Code config (settings.json — shared permissions and hooks)
.cursor/      generated Cursor rules (do not edit directly)
scripts/      install.sh, uninstall.sh, sync-cursor-rules.sh
```

## Adding a rule

1. Create `rules/<name>.md` with a `description:` frontmatter field
2. Add `@rules/<name>.md` to `CLAUDE.md`
3. Run `bash scripts/sync-cursor-rules.sh` to generate the Cursor equivalent

## Adding a skill and command

1. Create `skills/<name>/<name>.md`
2. Create `commands/<name>.md` with frontmatter and `@skills/<name>/<name>.md`
3. Re-run `bash scripts/install.sh` to symlink the new command globally

## Cursor

Cursor rules live in `.cursor/rules/` and are generated from `rules/` and `skills/python-patterns/`. The `PostToolUse` hook in `.claude/settings.json` auto-syncs them whenever a rule or the python-patterns skill is edited.
