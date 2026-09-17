# Loops — how to run one

A **loop** is a prompt for an agent that runs **on a schedule, unsupervised**, in a cloud
sandbox. Not a slash command you invoke, not a rule that shapes an interactive session —
something that wakes up on its own, does one bounded piece of work, reports, and exits.

Each file in this directory is a template. You copy nothing: the file is already in your
repo at `.agents/loops/`. You **fill in the config block at the top and leave the rest
untouched**, then point a scheduler at it.

**Loops are not tied to any one assistant.** A loop is plain markdown plus a schedule, so
whatever can run an agent against your repo can run one — a Cursor Automation, a Codex
cloud task, a Claude Code scheduled job, or a GitHub Actions cron that shells out to an
agent CLI. That is why they live in the vendor-neutral `.agents/` directory rather than
under `.claude/` or `.cursor/`.

This is the operating manual. If you are adding a *new* loop template to the `agents`
repo, see the "Adding a loop" section in that repo's root README instead.

## Tiers — what a loop is allowed to do

The number in the filename is the **blast radius of a single unattended tick**. It is the
one thing you should be able to read off the filename without opening it.

| Tier | May write | Reaches the default branch | Human authorization | Agents |
|---|---|---|---|---|
| **0** | nothing | never | none needed — read-only | one |
| **1** | test files only | only when a human merges the PR | none needed — tests can't change behaviour | one |
| **2** | production code | only when a human merges the PR | **per change**, before the agent starts | one |
| **3** | production code | **yes, unattended** | **per milestone**, granted in advance | four, coordinated by labels |

Tiers 0–2 all stop at "PR opened", so a human is always the last step before anything
lands. **Tier 3 is a different kind of thing** — it merges on its own, and the only
routine stop is a checkpoint class the loop detects for itself. Read its prerequisites
before turning it on.

## What's here

| Loop | Use it when |
|---|---|
| `tier-0-daily-health-scan.md` | You want a daily read-only signal on dependency vulnerabilities, leaked secrets and EOL risk. Safest possible starting point — it cannot write anything. |
| `tier-1-increase-test-coverage.md` | Coverage is thin and you want it filled in steadily, one module per PR, with zero risk to production code. |
| `tier-2-behavioural-improvements.md` | You have a specific, human-approved fix waiting and want an agent to execute it carefully with characterization tests. One PR at a time. |
| `tier-3-queue-driven-delivery.md` | You have a **queue of specified behaviours** to deliver and want four agents to build, review and merge them continuously. The heavyweight option. |

**Start at tier 0.** It costs nothing, it cannot damage anything, and a week of its Slack
output tells you whether scheduled agents are useful in your repo before you give one
write access.

## Adopting a loop

**1. Pick the lowest tier that does what you need.** Tier is a ceiling, not a target.

**2. Fill in the config block.** Every loop opens with:

```
## ── PER-REPO CONFIG (fill this in, leave the rest untouched) ──
REPO_NAME:         <e.g. proyecto_tesla>
SLACK_CHANNEL:     <#oees-code-health or per-repo channel>
MAX_OPEN_PRS:      2     # if this many automation PRs are already open, do NOT open another
## ─────────────────────────────────────────────────────────────
```

Rules for the block:

- A value in `<angle brackets>` is an **unfilled hint** describing what belongs there.
  Replace it. Numeric values with a trailing `#` comment are sensible defaults you can
  usually leave alone.
- The body refers to these as `{REPO_NAME}`, `{SLACK_CHANNEL}` and so on. **Nothing
  substitutes them** — there is no build step and no templating engine. The agent reads
  the config block at the top of the file and resolves the references itself as it goes.
- Because of that, **the config block and the body must stay in the same file**. Don't
  split a loop across files, and don't delete keys you think you don't need.
- Edit **only** the config block. Everything below it is the loop's logic, and changing
  it means you are maintaining a fork.

**3. Create anything the loop's Setup section asks for** — labels, branch protection, a
bot identity. Tier 3 has hard prerequisites; the lower tiers have few or none.

**4. Create the schedule.** See below.

**5. Watch it for a week** before trusting it. Every loop reports to `{SLACK_CHANNEL}`,
and "post nothing" is a valid, correct outcome for a tick with no work.

## Scheduling

A loop is not self-starting. Something has to run it. Any of these work, because all a
scheduler needs to do is launch an agent with a prompt:

| Scheduler | Where the schedule lives |
|---|---|
| Cursor | Cursor UI → Automations (prompt + cron) |
| Codex | a Codex cloud task on a schedule |
| Claude Code | a scheduled job / cron invoking the CLI |
| Anything else | GitHub Actions cron shelling out to an agent CLI |

Keep the scheduler prompt **thin** and let the committed file carry the instructions, so
the loop can be updated by a normal PR rather than by editing a prompt in a web UI:

```
Follow .agents/loops/tier-0-daily-health-scan.md
```

That one line is the whole prompt, and it is identical whichever tool you use.

**For anything that polls, put a cheap exit in the prompt itself:**

```
Run: gh pr list --state open --label "stage:req-check" --json number
If the result is empty, stop now and output nothing.
Otherwise follow .agents/loops/tier-3-queue-driven-delivery.md as role REQ-CHECKER.
```

Most ticks of a polling loop have no work. Without that guard, every idle tick loads the
whole file for nothing; with it, an idle tick is one API call. On a loop that ticks every
10 minutes, that is the difference between a real monthly bill and a rounding error.

**Cadence:** match it to how fast work actually appears, not to how quickly you'd like a
response. A checker that polls faster than work is produced is pure waste.

**A loop is never an always-on rule.** Loops are deliberately not exported to
`.cursor/rules/`, not imported into `CLAUDE.md`, and not registered as a Codex skill. They
are prompts a scheduler points at by path, and nothing else should load them. Wiring one
in as always-on guidance would put a merge robot's instructions into the context of every
interactive request in the repo — expensive, and wrong: a human editing a file should not
be reading from the same prompt as an unattended agent that merges to main.

## Stopping a loop

Know how to do this **before** you start one. Three ways, fastest first:

1. **The pause switch**, where a loop supports it — open an issue labelled `loop-paused`
   and the loop exits at its next tick. Needs only push rights, works from a phone, no
   scheduler access required. Close the issue to resume.
2. **Disable the schedule**, wherever it lives. Each loop's `KILL_SWITCH` config value
   should record exactly that: where the schedule lives and who owns it. Fill it in
   honestly — the person who needs it will not be you.
3. **Revoke the bot's write access.** Blunt, immediate, and leaves a mess to clean up.
   Last resort.

If a loop has no documented way to stop it, that is a bug in the loop. `scripts/check.sh`
in the `agents` repo warns about exactly this.

## When a loop misbehaves

| Symptom | Usually means |
|---|---|
| Silent — no Slack, no PRs, ever | The schedule isn't running, or a label the loop queries was never created. A query against a non-existent label returns empty, which is indistinguishable from "no work". |
| Posts "config incomplete" | An `<angle-bracket>` hint was left unfilled. The loop is refusing to guess, which is correct. |
| Opens PRs nobody asked for | The queue or authorization source is missing and the loop is inferring work. Stop it. A loop should never invent work — if this happens, treat the loop as faulty, not the backlog. |
| Same PR bouncing between stages | An item it cannot actually finish. Tier 3 caps this with `MAX_REJECTIONS` and parks the PR; on other loops, close the PR and mark the item for a human. |
| Work sits untouched for hours | A stage's schedule is dead, or its label is missing. Tier 3's merger sweeps for this; other loops have no watchdog, so check manually. |

## Before you turn on tier 3

It merges to your default branch with no human in the routine path. Beyond its Setup
section, one thing decides whether it will work at all:

> A queue row is eligible only if a checker who did not write the code can decide
> pass/fail from the row text plus its spec source alone.

"Reject a CUPS code with a bad control letter" clears that bar. "Refactor the billing
module" does not — nobody can pass or fail it objectively, so the review stages become
theatre while the loop merges unreviewed work. If your backlog is task titles rather than
statements about behaviour, tier 3 is the wrong tool. Use tier 2, where a human authorizes
each change.
