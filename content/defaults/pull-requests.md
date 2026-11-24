---
description: Draft until ready, a linked ticket and context, tasting notes, declared model assistance, small and chained, review only after the tests pass
---

# Pull requests

Default for OEES projects. A project opts out in its manifest.

## Open it as a draft

Open every pull request as a draft. Mark it ready for review when the work is complete and the checks pass. A draft tells the reviewer that the branch still moves.

Never request a review before the tests pass. A reviewer who reads a branch with a failing test reads code that will change.

## Write the description for the reviewer

Link the ticket. Then say what the change does and why the project needs it. "Please review this change" is not a description.

Add tasting notes: tell the reviewer where to look and what to check. Name the part that looks redundant or complex at a glance, so the reviewer spends attention there.

If a model helped with the change, say so and say how you verified the result. The author owns the code, whatever wrote the first draft.

## Keep it small

A small pull request gets a better review than a large one. If the work needs more than one pull request, chain them: each pull request takes the previous branch as its base. The reviewer then reads one step at a time.

Do not use a release branch to hold unfinished work. Merge the work behind a feature flag instead.

## Answer every comment

Acknowledge each comment. A 👍 reaction is enough when you agree and you make the change. Write a reply when you do not.

On a re-review, say what changed since the last pass. The reviewer must not look for it.

One approval is not always enough. If the change is complex or urgent, say so to the reviewers and ask for a second pair of eyes.

Exceptions: a revert of a broken change on the default branch can skip the draft stage and the tasting notes.
