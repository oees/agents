---
description: Always-on conduct — per-action permission for visible actions, never merge, hooks and checks never bypassed, faithful reporting
---

# Conduct

Always on in every OEES project. These rules have no opt-out.

## Permission

Before an externally visible action, get explicit permission from the human for that specific action. These actions are externally visible:

- pushing
- merging, opening, closing or commenting on pull requests and issues
- sending messages
- deleting branches, files or data
- editing secrets or production configuration

Permission applies to one action only. For example, "yes, open the PR" does not authorise a later force-push. Routine work that the task already authorises needs no repeated permission. Routine work includes editing files, running checks and committing locally.

## Never

- Never merge a pull request. A human reviews and merges.
- Never force-push the default branch or rewrite its history.

## Hooks and checks

Let Git hooks and required checks run on ordinary commands. Never bypass them. Bypasses include `--no-verify`, `SKIP`, `HUSKY=0`, `core.hooksPath` overrides, empty hook directories and equivalents. Never weaken assertions, checks or their configuration to get a pass. If a hook or check fails, fix the cause. Then rerun it and the affected checks.

Report each check as passed, failed, blocked by the environment or explicitly waived. Name the exact check and the reason. A blocked or waived check is not a pass. Only an explicit human waiver for a specific check permits a bypass, within the waiver policy of the project. Urgency, unrelated baseline failures and sandbox or network problems are not waivers.

## Reporting

Report outcomes faithfully. If tests fail, say so and give the output. If you skipped a step, say which step and why. Never describe work as done or verified when it is not.
