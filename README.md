# agents

Shared AI agents configuration for the Octopus Energy Spain engineering org — rules, skills, loops and commands that apply across every repo (if you so desire).

## Install

Run this from the root of any repo:

```bash
curl -fsSL https://raw.githubusercontent.com/oees/agents/main/scripts/bootstrap.sh | bash
```

That's it. The script fetches the latest tooling, installs the Claude Code and Cursor configuration, adds shared rules to `AGENTS.md` for Codex, and cleans up after itself. No permanent clone of this repo needed on your machine.

Then commit the result:

```bash
git add AGENTS.md .claude/ .cursor/
git commit -m "Add shared AI engineering guidance"
```

Once committed, every engineer on the repo gets the shared configuration. Claude Code picks up `.claude/`, Cursor picks up `.cursor/rules/`, and Codex reads `AGENTS.md`. Codex support currently covers the shared rules; the slash commands and skill discovery described below remain specific to Claude Code and Cursor.

### What the bootstrap does

1. Shallow-clones this repo into a temp directory
2. Runs `scripts/init-repo.sh` in your current directory
3. Deletes the temp clone

The generated layout:

```
AGENTS.md            # canonical rule bodies in a managed block — Codex reads these at startup
.claude/
  CLAUDE.md          # @imports for every rule — Claude Code loads these automatically
  rules/             # always-on behavioural rules
  commands/          # slash commands (/commit, /code-review, etc.)
  skills/            # skill definitions used by commands
  loops/             # scheduled cloud-agent templates (fill in the per-repo config block)
  settings.json      # recommended permissions and hooks (only written if not already present)
.cursor/
  rules/             # same rules as .mdc files — Cursor picks these up automatically
```

### Updating

Pull in the latest rules, commands, and skills by re-running the bootstrap from the repo root:

```bash
curl -fsSL https://raw.githubusercontent.com/oees/agents/main/scripts/bootstrap.sh | bash
```

Review and commit the diff — `AGENTS.md`, `.claude/` and `.cursor/` may change. Existing project instructions outside the managed block in `AGENTS.md` are preserved. Rules are intentionally stable so updates are infrequent and easy to audit.

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

**Rules** (loaded through each tool's configuration in adopting repos):

| Rule | Enforces |
|---|---|
| `tdd` | Write failing tests before implementation, red-green-refactor |
| `observability` | Structured logging, contextual errors, no silent exceptions |
| `code-quality` | Lint, format, type checks, tests, and security scans before merge |
| `no-inline-imports` | Imports at top of module only |
| `standards` | Frontend, backend, deployment, and API design conventions |
| `git` | Branch hygiene, commit standards, hooks stay enabled, no force-pushing main |
| `secrets` | No hardcoded credentials, use env vars and secret stores |
| `migrations` | Safe schema migrations — backwards-compatible, reversible, never drop data silently |

**Loops** (templates for unsupervised cloud agents that run on a schedule — copy one, fill in the per-repo config block at the top, leave the rest untouched):

| Loop | What it does |
|---|---|
| `tier-0-daily-health-scan` | Read-only daily scan for dependency vulnerabilities and health issues — posts a single Slack summary, never writes to the repo |
| `tier-1-increase-test-coverage` | Weekly test-coverage filler — opens small, reviewable PRs adding tests for one production module at a time |
| `tier-2-behavioural-improvements` | Behavioural-change fixer — opens at most one PR at a time, gated behind explicit human authorization |

---

## Structure of this repo

```
rules/        canonical always-on rules
skills/       skill definitions — command-backed actions and language guidance
commands/     slash command entry points
loops/        templates for scheduled, unsupervised cloud agents (tiers 0-2)
.claude/      Claude Code config for this repo (CLAUDE.md, settings.json — permissions and hooks)
.cursor/      generated Cursor rules (do not edit directly)
AGENTS.md     project guidance plus generated shared rules for Codex
scripts/
  bootstrap.sh      remote one-liner install (the main path)
  init-repo.sh      local install — run directly if you have this repo cloned
  install.sh        global install — symlinks into ~/.claude/ for all repos on your machine
  uninstall.sh      reverses install.sh
  sync-cursor-rules.sh  regenerates .cursor/rules/ from rules/ and skills/
  sync-codex-rules.sh   updates the managed AGENTS.md block from rules/
  check.sh          validates distribution, imports and Codex rule updates (run in CI)
```

## Global install (optional)

For Claude Code, if you want rules and commands active in *every* repo on your machine — not just repos that have `.claude/` committed — you can install globally:

```bash
bash scripts/install.sh   # requires this repo cloned locally
bash scripts/uninstall.sh # reverses the above
```

This adds rules to `~/.claude/CLAUDE.md` and symlinks commands and skills into `~/.claude/commands/` and `~/.claude/skills/`. Most people won't need this if their repos all use the bootstrap.

---

## Contributing

### Adding a rule

1. Create `rules/<name>.md` with a `description:` frontmatter field
2. Add `@rules/<name>.md` to `.claude/CLAUDE.md`
3. Run `bash scripts/sync-cursor-rules.sh` and `bash scripts/sync-codex-rules.sh` to regenerate the Cursor and Codex guidance

### Adding a skill and command

1. Create `skills/<name>/<name>.md`
2. Create `commands/<name>.md` with frontmatter and `@../skills/<name>/<name>.md` (the `../` resolves from `.claude/commands/` to `.claude/skills/`)

Changes are picked up by repos on their next bootstrap run. Run `bash scripts/check.sh` to validate distribution and confirm every command import still resolves.

### Adding a language pattern skill

Language guidance (e.g. Python, TypeScript) lives in `skills/<lang>-patterns/` as a skill — Claude auto-invokes it by its `description` when you work in that language, so it needs no command. To scope its Cursor rule to that language, add a `<lang> → globs` mapping in `scripts/sync-cursor-rules.sh` and run the script.

## Cursor

Cursor rules are generated from `rules/` and `skills/` into `.cursor/rules/*.mdc` and committed to this repo. The bootstrap copies them directly — no extra steps needed for per-repo installs. Each source maps to the matching Cursor rule type:

| Source | Cursor rule type | When it loads |
|---|---|---|
| `rules/*` | Always | every request |
| `skills/*-patterns/` | Auto Attached (glob-scoped) | while editing that language's files |
| other `skills/*` | Agent Requested (by `description`) | when Cursor's agent judges it relevant |

When contributing to this repo, run `bash scripts/sync-cursor-rules.sh` after editing a rule or skill to keep `.cursor/rules/` in sync. The `PostToolUse` hook in `.claude/settings.json` does this automatically when working in this repo.

## Codex

Codex [reads `AGENTS.md` at startup](https://learn.chatgpt.com/docs/agent-configuration/agents-md). The installer embeds every canonical rule directly in a marked block, so loading the policy does not depend on following links or interpreting Claude's `@imports`. Keep project commands and conventions outside that block; more specific project guidance still applies. Restart an existing Codex session after installing or updating guidance.

An `AGENTS.override.md` in the same directory takes precedence over `AGENTS.md`, and Codex's combined instruction size defaults to 32 KiB. Check for overrides and large instruction files, and verify the active instruction sources after restarting. The installer leaves overrides unchanged and warns if it finds one or the generated file alone exceeds that default limit.

In this tooling repo, run `bash scripts/sync-codex-rules.sh` after changing `rules/`. Use `bash scripts/sync-codex-rules.sh --check` to detect stale guidance without writing. Reinstallation replaces only the managed block, preserves local text, and rejects malformed markers or a symlinked `AGENTS.md` rather than overwriting them.

Git hooks run through ordinary Git commands in every client. Agents must fix failures and rerun checks; environmental blockers must be reported, never silently bypassed or called a pass. These instructions guide the agent; repository hooks and CI provide the checks.

Claude's `.claude/settings.json` tool hooks are separate from Git hooks. Codex lifecycle hooks use [their own configuration and trust review](https://learn.chatgpt.com/docs/hooks); this installer does not configure or trust them. In Codex, run the regeneration commands and checks documented in this repo explicitly. Do not assume Claude's `PostToolUse` hook ran.
