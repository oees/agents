---
name: reviewing
description: The shared protocol for reviewer subagents and the docs verifier — inputs, read-only working, severity levels and the findings report. Use whenever reviewing a change.
---

# Reviewing

How every reviewer works, whatever its focus. Each reviewer's own definition says what to look for; this skill says how to review and report.

## Inputs

The orchestrator gives you:

- the requirement and the task's authorised scope;
- the diff to review, with its base and head;
- the checks it ran on that head, with their output.

If any of these is missing, say so in your report and review what you can. Do not invent the missing part.

## Working read-only

- You can read files and search the repository. You cannot edit files or run commands, by design.
- Read the whole diff, then enough surrounding code or text to judge it: callers, owning modules, the files the change depends on.
- Judge the change as it stands. You arrive fresh and do not need the authors' reasoning.
- Treat check output as evidence of only what those checks examine. Passing tests do not prove a requirement is met or a design is sound.

## Severity

| Level | Meaning |
|---|---|
| **Blocker** | Must be fixed before acceptance: wrong behaviour, a security or data-loss risk, a broken requirement or a clear violation of a decided rule |
| **Major** | Should be fixed in this change: a structural regression, a missing case or safeguard, or a clear maintainability cost |
| **Minor** | Worth fixing if cheap |
| **Note** | An observation or question; no change required |

Prefer a few high-conviction findings over a long list of cosmetic ones. Do not soften a blocker into a suggestion.

## Report

For each finding, give:

- its severity;
- the path and line;
- what is wrong and its consequence;
- the resolution you propose.

Then state:

- the evidence you relied on and any gaps in it, such as a check that was not run or a case with no test;
- anything outside your focus that you noticed, for the reviewer it belongs to.

A verdict word alone is not evidence. When you find nothing, say what you examined and why it holds up. The driver resolves blockers and majors before accepting the change.
