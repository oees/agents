# Software Engineering Audit — agents

- **Audited:** 2026-07-11, on branch `main` (pulled same day)
- **What it is:** Shared AI-agent tooling for the Octopus Energy Spain org: always-on rules, slash commands, skills, and scheduled-loop templates, distributed into other repos via a `curl | bash` bootstrap that copies files into `.claude/` and `.cursor/`.
- **Size:** ~53 files, all Markdown + shell. No application code.

## Scorecard

| Dimension | Rating | Summary |
|---|---|---|
| Code quality | Good | Disciplined shell (`set -euo pipefail`, traps, quoting); clear docs |
| Maintainability | Good | Single source of truth in `rules/`+`skills/`, generated `.cursor/` tree, CI validates imports |
| Security | Fair | `curl | bash` distribution is the only notable exposure |
| Deployment | Good | Nothing to deploy; CI (`tooling-ci.yml`) runs `check.sh` on every PR |
| Complexity balance | Good | Right-sized; generation script instead of hand-maintained duplicates |

## Strengths (keep these patterns)

- `scripts/check.sh` validates in CI that every `@import` in generated commands and `CLAUDE.md` resolves — broken references cannot reach `main`.
- One canonical source (`rules/`, `skills/`) with `sync-cursor-rules.sh` generating the Cursor `.mdc` mirror, plus a `PostToolUse` hook keeping them in sync while editing.
- README documents an inspect-before-run alternative to the `curl | bash` one-liner.

## Findings

### 1. MEDIUM — `curl | bash` distribution has no integrity check
**Where:** `scripts/bootstrap.sh` (and the README one-liner).
**What:** Repos across the org execute whatever is on `main` of this repo at install time. Anyone who can push to `main` here can inject rules/hooks (including `settings.json` permissions and `PostToolUse` hooks) into every consuming repo on its next bootstrap. This is an org-internal supply-chain concentration point, not an internet-facing one, so severity is moderate.
**How to fix:**
1. Enable branch protection on `main` of this repo: require PR review, disallow force pushes and direct pushes. This is the single highest-leverage mitigation and needs no code.
2. Optionally, have `bootstrap.sh` print the cloned commit SHA it installed from, so consuming repos' commit diffs record provenance.
3. Do not build a signing pipeline — disproportionate for internal tooling.

### 2. LOW — `settings.json` distributed permissions deserve periodic review
**What:** The bootstrap copies a recommended `.claude/settings.json` (permissions and hooks) into consuming repos when absent. Any permission widening here propagates org-wide silently on the next bootstrap.
**How to fix:** Add a line to `CONTRIBUTING.md` requiring that PRs touching `.claude/settings.json` or any `hooks` entry get an explicit second review. No tooling needed.

### 3. LOW — Loops templates carry operational authority; document a kill switch
**Where:** `loops/tier-*.md` (scheduled unsupervised cloud agents, tier 2 can open PRs).
**How to fix:** In each loop template header, state how to disable the loop (where the schedule lives, who owns it) so an on-call engineer can stop a misbehaving loop without archaeology.

## What NOT to do

- Don't convert scripts to Python or add a package manager — plain POSIX-ish bash with `set -euo pipefail` is appropriate here.
- Don't add versioning/releases for the tooling; "consume latest main + review the diff on bootstrap" is a sane model at this scale, provided finding #1's branch protection is in place.
