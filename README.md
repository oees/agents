# agents

Shared Claude Code configuration for the Octopus Energy Spain engineering org — rules, skills, and commands that apply across every repo.

## Install

Run this from the root of any repo:

```bash
curl -fsSL https://raw.githubusercontent.com/oees/agents/main/scripts/bootstrap.sh | bash
```

That's it. The script fetches the latest tooling, copies it into `.claude/` inside your repo, and cleans up after itself. No permanent clone of this repo needed on your machine.

Then commit the result:

```bash
git add .claude/ .cursor/
git commit -m "chore: add Claude Code and Cursor tooling"
```

Once committed, every engineer on the repo gets rules, commands, and skills automatically — no per-developer setup required. Claude Code picks up `.claude/` and Cursor picks up `.cursor/rules/` on first launch.

### What the bootstrap does

1. Shallow-clones this repo into a temp directory
2. Runs `scripts/init-repo.sh` in your current directory
3. Deletes the temp clone

The generated layout:

```
.claude/
  CLAUDE.md          # @imports for every rule — Claude Code loads these automatically
  rules/             # always-on behavioural rules
  commands/          # slash commands (/commit, /code-review, etc.)
  skills/            # skill definitions used by commands
  settings.json      # recommended permissions and hooks (only written if not already present)
.cursor/
  rules/             # same rules as .mdc files — Cursor picks these up automatically
```

### Updating

Pull in the latest rules, commands, and skills by re-running the bootstrap from the repo root:

```bash
curl -fsSL https://raw.githubusercontent.com/oees/agents/main/scripts/bootstrap.sh | bash
```

Review and commit the diff — both `.claude/` and `.cursor/` may change. Rules are intentionally stable so updates are infrequent and easy to audit.

### If you prefer to inspect before running

Download the script, review it, then execute:

```bash
curl -fsSL https://raw.githubusercontent.com/oees/agents/main/scripts/bootstrap.sh -o bootstrap.sh
# read bootstrap.sh and scripts/init-repo.sh before proceeding
bash bootstrap.sh && rm bootstrap.sh
```

---

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

**Rules** (always-on in every Claude Code session on this repo):

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

---

## Structure of this repo

```
rules/        canonical always-on rules
skills/       skill definitions referenced by commands
commands/     slash command entry points
.claude/      Claude Code config for this repo (settings.json — permissions and hooks)
.cursor/      generated Cursor rules (do not edit directly)
scripts/
  bootstrap.sh      remote one-liner install (the main path)
  init-repo.sh      local install — run directly if you have this repo cloned
  install.sh        global install — symlinks into ~/.claude/ for all repos on your machine
  uninstall.sh      reverses install.sh
  sync-cursor-rules.sh  regenerates .cursor/rules/ from rules/ and python-patterns
```

## Global install (optional)

If you want rules and commands active in *every* repo on your machine — not just repos that have `.claude/` committed — you can install globally:

```bash
bash scripts/install.sh   # requires this repo cloned locally
bash scripts/uninstall.sh # reverses the above
```

This adds rules to `~/.claude/CLAUDE.md` and symlinks commands into `~/.claude/commands/`. Most people won't need this if their repos all use the bootstrap.

---

## Contributing

### Adding a rule

1. Create `rules/<name>.md` with a `description:` frontmatter field
2. Add `@rules/<name>.md` to `CLAUDE.md`
3. Run `bash scripts/sync-cursor-rules.sh` to generate the Cursor equivalent

### Adding a skill and command

1. Create `skills/<name>/<name>.md`
2. Create `commands/<name>.md` with frontmatter and `@skills/<name>/<name>.md`

Changes are picked up by repos on their next bootstrap run.

## Cursor

Cursor rules are generated from `rules/` and `skills/python-patterns/` into `.cursor/rules/*.mdc` and committed to this repo. The bootstrap copies them directly — no extra steps needed for per-repo installs.

When contributing rules to this repo, run `bash scripts/sync-cursor-rules.sh` after editing a rule to keep `.cursor/rules/` in sync. The `PostToolUse` hook in `.claude/settings.json` does this automatically when working in this repo.
