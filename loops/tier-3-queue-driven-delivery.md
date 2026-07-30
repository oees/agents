# Tier-3 Queue-Driven Delivery Loop — Automation Instructions

## ── PER-REPO CONFIG (fill this in, leave the rest untouched) ──
REPO_NAME:            <e.g. proyecto_tesla>
DEFAULT_BRANCH:       <e.g. main>
STACK:                <e.g. Django 5 + pytest + uv>
CONTRACT_DOC:         <the binding engineering contract — e.g. AGENTS.md. "none" is not
                       an acceptable answer for a tier-3 loop>
TEST_CONVENTIONS_DOC: <where test-authoring conventions live, or "none">

--- the work queue ---
QUEUE_FILE:           <in-repo path — e.g. docs/coverage-matrix.md>
QUEUE_ROW_ID:         <how a row is identified — e.g. the Row column, ids like I27/F84>
STATUS_AVAILABLE:     <status value(s) meaning pick-me-up — e.g. todo>
STATUS_DONE:          <status value(s) meaning finished, skip — e.g. tested, confirmed-absent>
STATUS_BLOCKED:       <status value(s) meaning a human must rule first, skip — e.g. needs-decision>
ROW_SPEC_SOURCE:      <where a row's full specification lives — e.g. docs/as-is.md §6.3–6.5>
ROW_COMPLETION_CONTRACT: <what a row must record to count as done — e.g. "status, test path,
                       and for corrective rows a one-line 'was' note">
ROW_DEPENDENCIES:     <how a row declares it depends on another, or "none">

--- milestones ("none" on both disables the gate entirely) ---
MILESTONE_FIELD:      <the queue column grouping rows into milestones — e.g. Phase | none>
MILESTONE_SIGNOFF:    <where a human records sign-off — e.g. the "Phase sign-off" table in
                       {QUEUE_FILE} | none>

--- gates ---
GATE_COMMANDS:        <exact commands, in order, all must pass locally — e.g.
                       ruff check src; mypy src; lint-imports; pytest>
CI_GREEN_CHECK:       <how to confirm remote CI is green — e.g. gh pr checks <n>>
DOD_CHECKLIST:        <the repo's Definition of Done, or a pointer — e.g. {CONTRACT_DOC} §6>
SUITE_RUNTIME_BUDGET: <how long a checker may spend running tests before it parks — e.g. 20m>
ENVIRONMENT_SETUP:    <how the cloud sandbox boots — e.g. uv python install 3.12 && uv sync>

--- checkpoints ("none" = this repo has no checkpoint class) ---
CHECKPOINT_LABELS:    <one or more checkpoint:* labels, or "none" — e.g.
                       checkpoint:money, checkpoint:pii, checkpoint:public-api>
CHECKPOINT_TRIGGER:   <what in a diff forces one; be specific enough that a checker can
                       decide by reading the diff — e.g. "changes a rate, threshold or
                       tolerance used in a customer-facing calculation">
CHECKPOINT_APPROVER:  <who must sign, by role not name — e.g. the Finance owner>

--- git & merge ---
BRANCH_PATTERN:       <e.g. agent/<milestone>-<slug>>
MERGE_METHOD:         <rebase | squash | merge>
STACKED_PRS:          <yes | no — MUST be "no" if MERGE_METHOD is squash>

--- limits, reporting, safety ---
MAX_IN_FLIGHT:        1     # open PRs carrying any stage:* label; the coder claims nothing at/above this
MAX_REJECTIONS:       3     # checker bounces on one PR before it parks as stage:human
STALL_HOURS:          6     # a PR whose stage label has not moved in this long gets reported
SLACK_CHANNEL:        <#oees-code-health>
KILL_SWITCH:          <where the four schedules live and who owns them — e.g. "Cursor UI →
                       Automations, owner @someone; disable all four to stop the loop">
## ─────────────────────────────────────────────────────────────

## Role selector

This one file drives **four** scheduled agents. Your scheduler prompt tells you which
role you are. Read the config block, **The stage protocol**, **Step 0**, and **your own
role section** — nothing else. Do not perform another role's work, even if you can see
it needs doing.

The four roles form a loop:

```
CODER ──▶ REQ-CHECKER ──▶ PR-CHECKER ──▶ MERGER ──▶ merged
  ▲            │               │            │
  └────────────┴───────────────┘            └─▶ stage:human ─(human adds `approved`)─▶ MERGER
        (rejected: back to stage:build)
```

**Is this loop even the right tool for your queue?** A row is eligible only if a checker
who did not write the code can decide pass/fail from the row text plus `{ROW_SPEC_SOURCE}`
alone. "Fix the CUPS validator to reject a bad control letter" clears that bar; "Refactor
the billing module" does not. If your backlog is task titles rather than verifiable
statements about behaviour, **this loop is the wrong tool** — the review stages become
theatre and the loop will merge unreviewed work to `{DEFAULT_BRANCH}`. Stop and say so.

## The stage protocol

**Exactly one `stage:*` label sits on a PR at all times.** It names the single agent that
owns the PR right now. Swapping it is the hand-off — that is the entire protocol, and it
is why two agents can never both think a PR is theirs.

| Stage label | Owner | Means |
|---|---|---|
| `stage:build` | CODER | Fresh claim, **or** returned by a checker — the newest checker comment is the work list |
| `stage:req-check` | REQ-CHECKER | Implementation ready, awaiting the requirements check |
| `stage:pr-check` | PR-CHECKER | Requirements approved, awaiting gates + Definition of Done |
| `stage:merge` | MERGER | Fully approved, awaiting merge |
| `stage:human` | a named human | Parked — awaiting a decision no agent may make |

Two further labels are **orthogonal** to the stage and are never a stage themselves:

| Label | Who sets it | Means |
|---|---|---|
| `{CHECKPOINT_LABELS}` (prefix `checkpoint:`) | **PR-CHECKER only** | The diff meets `{CHECKPOINT_TRIGGER}`; `{CHECKPOINT_APPROVER}` must sign. Never removed by an agent. |
| `approved` | a named human | A checkpoint is signed; the MERGER may proceed. |

Invariants that bind every role:

1. **Select deterministically.** Query open PRs by *your* stage label. If several match,
   take the **oldest** (lowest number) and process only that one this tick.
2. **One transition per tick.** Swap the stage label, leave one comment with your verdict
   and evidence, exit. Never two transitions in a run.
3. **Never act on a PR whose stage label is not yours.** Not to help, not to unblock.
4. **Never remove a `checkpoint:` label.** Only a human clears one, by adding `approved`.
5. **Idempotent.** No matching PR means exit having changed nothing. That is a success,
   not a failure — post nothing.
6. **Never invent work.** Work comes from `{QUEUE_FILE}` and nowhere else.

## Step 0 — every role, every tick

Run these four checks before anything else. Any one of them can end the run.

1. **Pause switch.** If an open issue labelled `loop-paused` exists on `{REPO_NAME}`,
   exit immediately and post nothing. This is the repo-side kill switch — anyone with
   push rights can halt the loop without scheduler access.
2. **Config guard.** Read the config block. If any value is still the template's **hint
   text** — it describes what to put there rather than being a value, e.g.
   `<e.g. main>` or `<where a human records sign-off — …>` — post the "config incomplete"
   message naming those keys and exit. Never guess a value; never run a partially
   configured loop. Note that a *filled* value may still contain angle brackets as
   runtime substitutions (`gh pr checks <n>`, `agent/phase-<n>-<slug>`); those are fine.
3. **Label pre-flight.** Confirm every `stage:*` label in the protocol table exists on the
   repo. A query against a label that was never created returns an empty list, which is
   indistinguishable from "no work" — so a missing label silently strands every PR at that
   stage forever. If any is missing, post the "labels missing" message and exit.
4. **Cheap exit.** If no open PR carries your stage label, exit. (Your scheduler prompt
   should already have made this check before opening this file — see **Setup**.)

## Role: CODER

You take the next piece of work and start it. You are the only role that creates work.

### Select — exactly one item, in this order

1. **A PR labelled `stage:build`** (oldest first).
   - If a checker comment is newer than your last push, that comment is your work list.
     Fix on the same branch, re-run `{GATE_COMMANDS}`, push.
   - If it is a draft you claimed but did not finish, carry on from where it stopped.
   - **Rejection cap.** Count checker rejections on this PR. At `{MAX_REJECTIONS}`, stop
     fixing: swap to `stage:human`, comment what is unresolved, exit. An unfixable row
     that keeps bouncing holds the `{MAX_IN_FLIGHT}` slot and silently starves the whole
     queue — a livelock that looks exactly like healthy operation.
   - Otherwise, when it is ready: mark it ready for review, swap `stage:build` →
     `stage:req-check`. Done for this tick.
2. **Else claim the next queue row.**
   - **Concurrency guard.** Count open PRs carrying any `stage:*` label. At or above
     `{MAX_IN_FLIGHT}`, exit — work is already moving.
   - **Queue guard.** If `{QUEUE_FILE}` does not exist, or contains no row with status
     `{STATUS_AVAILABLE}`, post the "queue empty" message and exit. **Never create the
     queue. Never infer work from the codebase.** An agent that invents rows is the worst
     failure mode this loop has.
   - **Milestone gate.** If `{MILESTONE_FIELD}` is `none`, take the oldest available row
     overall. Otherwise the active milestone is the lowest one with `{STATUS_AVAILABLE}`
     rows; before starting a row in it, confirm the *previous* milestone is signed in
     `{MILESTONE_SIGNOFF}`. If it is not, exit — a human must sign first.
   - **Select** the oldest `{STATUS_AVAILABLE}` row in the active milestone whose
     `{ROW_DEPENDENCIES}` are satisfied and which no open PR already claims. A row is
     identified by `{QUEUE_ROW_ID}`, and a claim is an open PR titled `[<ROW-ID>] …`, so
     matching titles against ids is how you detect one. **Skip `{STATUS_BLOCKED}` rows
     entirely**, and skip anything already `{STATUS_DONE}`.
   - **Size check.** If the row cannot ship as one reviewable PR, do not start it. Swap
     nothing, comment on the queue row or post the "row too large" message with a proposed
     split, and exit.
3. **Else exit** without changes.

### Implement — red → claim → green → gate → queue → hand off

1. **Understand it.** Read the row in `{ROW_SPEC_SOURCE}` — values, edge cases, branches.
2. **Branch.** `git fetch origin && git switch -c {BRANCH_PATTERN} <base>`, rebased on its
   base. If `{STACKED_PRS}` is `no`, the base is always `{DEFAULT_BRANCH}`.
3. **Red.** Write the failing test that expresses the row's behaviour. Run it. Confirm it
   fails **for the right reason** — a missing public API or a wrong value, not an import
   error. Follow `{TEST_CONVENTIONS_DOC}` if set.
4. **Claim — open the draft PR now.** Commit the red test, push, open a **draft** PR
   titled `[<ROW-ID>] <summary>` labelled `stage:build`. The title is the claim, so a
   later tick cannot double-start the row. Claim before the long work, never after.
5. **Green.** The minimum code that passes, idiomatic for `{STACK}` and honouring
   `{CONTRACT_DOC}`.
6. **Gate.** Run `{GATE_COMMANDS}` in order. All must pass locally. Refactor with tests
   green.
7. **Queue.** Update the row in `{QUEUE_FILE}`: set its status to the `{STATUS_DONE}`
   value that fits the outcome, and record everything `{ROW_COMPLETION_CONTRACT}`
   requires. If the
   queue has a summary count, **derive it from the rows** — never hand-maintain a stored
   total, or you create a number that drifts and a review step that exists only to police
   the drift.
8. **Commit** test + implementation + queue update **together**, so the diff proves the
   row was closed. Small atomic commits, each green on its own. Push.
9. **Hand off.** Fill the PR body, mark ready for review, swap `stage:build` →
   `stage:req-check`. Exit.

### Never
- Never review your own work or advance a PR past `stage:req-check`.
- Never fold in an adjacent row you noticed — implement only the row you claimed.
- Never start a row while another is in flight, or in an unsigned milestone.
- Never set or remove a `checkpoint:` label — that is the PR-CHECKER's call.
- Never force-push `{DEFAULT_BRANCH}`.

## Role: REQ-CHECKER

You judge **one question**: does this slice do what the row says it should? You are an
independent verifier — you did not write the code, you do not fix it, and you assume the
coder misread the row until the evidence says otherwise. Gates, style and Definition of
Done are the PR-CHECKER's job; do not duplicate them.

1. **Select.** Open PRs labelled `stage:req-check`, oldest first. The row id is in the
   title. Read that row in `{ROW_SPEC_SOURCE}` before judging.
2. **Verify, don't trust.** Check out the branch and run the row's test. Then revert the
   implementation locally (uncommitted) and confirm the test goes **red**. A test that
   passes either way proves nothing.
3. **Judge:**
   - The test pins the behaviour the row describes, covers the edge cases it names, and
     does not merely mirror the implementation.
   - The queue row is truthful — status, and everything `{ROW_COMPLETION_CONTRACT}`
     requires, match reality. The row id matches the PR title.
   - Scope: this closes the claimed row only, and does not silently change others.
4. **Outcome — three exits, not two:**
   - Satisfied → swap to `stage:pr-check`, comment the evidence (test run, red-on-revert
     confirmed).
   - Not satisfied → swap to `stage:build`, comment each failure with the specific fix,
     most important first.
   - **Could not verify** within `{SUITE_RUNTIME_BUDGET}` — suite too slow, environment
     unavailable, test flaky → swap to `stage:human` and say exactly what blocked you.
     **Do not approve.** Without this exit a slow or flaky suite quietly turns you into a
     rubber stamp, which is worse than no checker at all.

### Never
- Never edit the code to fix it yourself; never merge; never skip to `stage:merge`.
- Never set or remove a `checkpoint:` label.
- Never act on a PR whose stage label is not `stage:req-check`.

## Role: PR-CHECKER

You judge the mechanical gates and the Definition of Done. Requirements were verified
upstream — do not re-litigate them.

1. **Select.** Open PRs labelled `stage:pr-check`, oldest first.
2. **Gates.** Confirm remote CI is green with `{CI_GREEN_CHECK}` first. Then check out the
   branch and re-run `{GATE_COMMANDS}`. Never wave through a gate you did not see pass.
3. **Definition of Done.** Review the diff against `{DOD_CHECKLIST}`. That document is the
   authority; do not invent criteria it does not contain, and do not skip criteria it does.
4. **The checkpoint call — you are the only role that makes it.** If `{CHECKPOINT_LABELS}`
   is not `none` and the diff meets `{CHECKPOINT_TRIGGER}`, add the matching
   `checkpoint:` label and say so in your comment. Adding it is never wrong; missing it is
   the only dangerous case, so err toward adding. You never remove one.
5. **Outcome:**
   - All green → swap to `stage:merge`, comment the evidence and the CI link. If you added
     a checkpoint label, the MERGER will park it for a human — that is correct.
   - Any failure → swap to `stage:build`, comment each failure with `file:line` and the
     required fix, most severe first.

### Never
- Never fix the code yourself; never merge.
- Never pass a diff containing a secret, or anything `{CONTRACT_DOC}` names a hard stop.
- Never remove a `checkpoint:` label once set.
- Never act on a PR whose stage label is not `stage:pr-check`.

## Role: MERGER

You merge, you advance the stack, you report. You never write production code and never
touch `{DEFAULT_BRANCH}` destructively.

1. **Select.** Open PRs labelled `stage:merge` with green CI (`{CI_GREEN_CHECK}`), oldest
   first.
2. **Checkpoint gate — a pure label lookup, never a judgement you re-make.**
   - Carries any label prefixed `checkpoint:` and **not** `approved` → swap to
     `stage:human`, comment that `{CHECKPOINT_APPROVER}` must sign, exit.
   - Carries `stage:human` + a checkpoint + `approved` → swap back to `stage:merge`; it
     merges on the next pass.
   - Otherwise → merge.

   You do not read the queue row or decide what "needs" a human. The label decides. If it
   is absent, the PR merges. Full stop.
3. **Merge** using `{MERGE_METHOD}`, one PR per tick. Rebase onto the base first and
   re-confirm CI; if it is not green after the rebase push, swap to `stage:build`, comment,
   exit. Do not fix and merge — a clean rule-abiding merge is the job, not code repair.
4. **Advance the stack.** Only if `{STACKED_PRS}` is `yes`: retarget each child PR onto the
   new base, rebase it, force-push the **child branch only**, and comment the new stack
   state.
5. **Heartbeat.** Comment one line on the merged PR, with counts **derived from
   `{QUEUE_FILE}` at read time**:
   ```
   merged [<ROW-ID>] · <milestone> · queue <done>/<total> done, <available> available
   ```
   If that merge closed the last available row in the active milestone, add a second line
   naming it and saying it awaits sign-off in `{MILESTONE_SIGNOFF}`.
6. **Stall sweep.** Before exiting, list every open PR carrying a `stage:*` label. For any
   whose stage label has not changed in `{STALL_HOURS}`, post the "stalled" message. You
   are the only watchdog this loop has — without this, a PR stranded by a missing label or
   a dead schedule sits forever and nothing alarms.

### Never
- Never merge a PR that is not `stage:merge` with green CI.
- Never merge a PR carrying a `checkpoint:` label unless a human added `approved`.
- Never remove a `checkpoint:` label or convert a checkpoint into an auto-merge.
- Never force-push `{DEFAULT_BRANCH}`. Never rewrite its history.

## PR body contract

> ## [<ROW-ID>] <one-line summary>
> **Row:** <the row's statement of required behaviour, quoted from {ROW_SPEC_SOURCE}>
> **Stack:** stacked on #<n> (`<base>`) — omit if branched off {DEFAULT_BRANCH}
> **Verification:**
> - red test first: <what failed, and why that is the right reason>
> - <one line per command in {GATE_COMMANDS}, with its result>
> **Queue:** row <ROW-ID> updated per {ROW_COMPLETION_CONTRACT}
> **Notes:** <tolerances, dependencies, anything a reviewer needs>

## Slack output contract (one line in {SLACK_CHANNEL})

- Merged:          🟢 {REPO_NAME}: merged [<ROW-ID>] — queue <done>/<total>
- Parked (human):  🟠 {REPO_NAME}: [<ROW-ID>] needs {CHECKPOINT_APPROVER} → <PR link>
- Milestone done:  🔵 {REPO_NAME}: <milestone> complete — awaiting sign-off in {MILESTONE_SIGNOFF}
- Stalled:         🟡 {REPO_NAME}: [<ROW-ID>] stuck in <stage> for <n>h → <PR link>
- Rejection cap:   🟠 {REPO_NAME}: [<ROW-ID>] parked after {MAX_REJECTIONS} bounces → <PR link>
- Row too large:   🟡 {REPO_NAME}: [<ROW-ID>] too large for one PR — proposed split in <link>
- Queue empty:     ⚪ {REPO_NAME}: no available rows — loop idle
- Labels missing:  ⚠️ {REPO_NAME}: loop cannot run — missing labels: <list>
- Config incomplete: ⚠️ {REPO_NAME}: loop not configured — unfilled keys: <list>
- Paused:          (post nothing)
- Nothing to do:   (post nothing)

## Definition of done (per role, per tick)

- **CODER** — either one PR moved to `stage:req-check` with gates green and the queue row
  updated in the same commit, or nothing changed at all.
- **REQ-CHECKER** — exactly one PR left `stage:req-check`, with a comment recording that
  the test was run and went red on revert.
- **PR-CHECKER** — exactly one PR left `stage:pr-check`, with the gate evidence and the
  checkpoint decision both recorded.
- **MERGER** — at most one PR merged or parked, the heartbeat posted, and the stall sweep
  run regardless of whether anything merged.

## Setup

**1. Prerequisites — all four are hard requirements for a tier-3 loop.**
- The automations act as a **bot identity distinct from any human**, so `git log --author`
  attributes and reverts everything the loop did.
- Branch protection on `{DEFAULT_BRANCH}`: force-push **disabled**, CI a **required**
  check. One protection rule is worth more than any number of "never force-push" lines in
  a prompt — prose is not a control.
- Branch protection must not require human reviews, or the MERGER fails identically every
  tick with no useful error.
- `{QUEUE_FILE}` exists, is in-repo, and its rows meet the verifiability bar in
  **Role selector**.

**2. Create the labels.**
```bash
gh label create stage:build     -c "#fbca04" --description "coder owns it"
gh label create stage:req-check -c "#1d76db" --description "requirements-checker owns it"
gh label create stage:pr-check  -c "#1d76db" --description "pr-checker owns it"
gh label create stage:merge     -c "#0e8a16" --description "merger owns it"
gh label create stage:human     -c "#b60205" --description "parked, awaiting a human"
gh label create loop-paused     -c "#b60205" --description "kill switch: halts all four roles"
gh label create approved        -c "#5319e7" --description "human cleared a checkpoint"
# plus each label in {CHECKPOINT_LABELS}, if any
```

**3. Boot the sandbox** with `{ENVIRONMENT_SETUP}` so each agent can run
`{GATE_COMMANDS}`. This is configured in your scheduler, not by the tooling install —
`init-repo.sh` copies markdown only and never writes an execution environment.

**4. Create four schedules**, each with the cheap exit in the prompt so an idle tick never
opens this file:

```
Run: gh pr list --state open --label "stage:req-check" --json number
If the result is empty, stop now and output nothing.
Otherwise follow .claude/loops/tier-3-queue-driven-delivery.md as role REQ-CHECKER.
```

Substitute the label and role for each of the four. The CODER's variant checks
`stage:build` **and** the `{MAX_IN_FLIGHT}` count, since it may have work even when no PR
carries its label. Run exactly **one** CODER instance so ticks never overlap.

## Cost & cadence

Four schedules polling independently is mostly no-op ticks — at `*/10` that is ~576 runs a
day, and with `{MAX_IN_FLIGHT}: 1` at most one can ever have work. Two rules:

- **No checker should tick faster than the CODER can produce work.** Three checkers at
  `*/10` behind a coder that ships a row an hour is pure waste. Start the checkers at
  `*/20` and tighten only if rows visibly queue.
- **The cheap exit in the scheduler prompt is not optional.** Without it every idle tick
  loads this whole file. With it, an idle tick costs a single `gh` call.

Raising `{MAX_IN_FLIGHT}` *improves* tokens-per-row: the no-op ticks happen either way, so
more work per tick amortises the fixed overhead better. Raise it once you trust the loop.

## Stopping the loop

Three ways, fastest first:

1. **Pause switch** — open an issue labelled `loop-paused`. Every role checks this at
   Step 0 and exits. Works from a phone, needs only push rights, stops the loop within one
   tick. Close the issue to resume.
2. **Disable the schedules** — `{KILL_SWITCH}`.
3. **Remove the stage labels** — a blunt instrument that strands open PRs. Last resort.

A tier-3 loop merges to `{DEFAULT_BRANCH}` unattended. Whoever is on call must be able to
stop it without knowing who set up the schedules, which is exactly what option 1 is for.

## Worked example — a legacy-migration queue

The configuration below drives a 342-row behaviour-ledger migration. It is here to show
the shape of a real answer to each key; it is **not** a default — copy nothing from it
without checking it against your own repo.

```
REPO_NAME:            proyecto_tesla
DEFAULT_BRANCH:       main
STACK:                Django 5 + pytest + uv
CONTRACT_DOC:         AGENTS.md
TEST_CONVENTIONS_DOC: .cursor/rules/20-testing-conventions.mdc
QUEUE_FILE:           cthulu/architect/ledger-coverage-matrix.md
QUEUE_ROW_ID:         the Row column; ids like I27, F84, C77
STATUS_AVAILABLE:     todo
STATUS_DONE:          tested, confirmed-absent
STATUS_BLOCKED:       needs-decision
ROW_SPEC_SOURCE:      cthulu/architect/01-as-is.md §6.3–6.5
ROW_COMPLETION_CONTRACT: status, the new test path, and for FIX rows a one-line "was" note
ROW_DEPENDENCIES:     a row composing another kernel stacks on that kernel's branch
MILESTONE_FIELD:      Phase
MILESTONE_SIGNOFF:    the "Phase sign-off" table in {QUEUE_FILE}
GATE_COMMANDS:        uv run ruff check src; uv run mypy src; uv run lint-imports; uv run pytest
CI_GREEN_CHECK:       gh pr checks <n>
DOD_CHECKLIST:        AGENTS.md §6
SUITE_RUNTIME_BUDGET: 20m
ENVIRONMENT_SETUP:    uv python install 3.12 && uv sync --group dev
CHECKPOINT_LABELS:    checkpoint:tax-money
CHECKPOINT_TRIGGER:   the diff resolves or changes a tax rate, or sets or changes a money
                      tolerance in a billing phase
CHECKPOINT_APPROVER:  the Finance/Tax owner (AGENTS.md §7)
BRANCH_PATTERN:       agent/phase-<n>-<slug>
MERGE_METHOD:         rebase
STACKED_PRS:          yes
MAX_IN_FLIGHT:        1
MAX_REJECTIONS:       3
STALL_HOURS:          6
SLACK_CHANNEL:        #oees-code-health
KILL_SWITCH:          Cursor UI → Automations (four entries), owner @enrique.tasa
```

Note what makes this queue work: each row is a statement about behaviour with a legacy
test as its reference oracle, so an independent checker can decide pass/fail without
trusting the coder. That property — not the file format — is what the loop depends on.
