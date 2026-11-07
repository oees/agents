---
description: Rebase onto the default branch, no merge commits, no squashing, commits that stand alone
---

# Git

Default for OEES projects. A project opts out in its manifest.

Always rebase onto the target branch instead of merging. No merge commits on the default branch. Detect the default branch rather than assuming its name; the project context names it, and Git reports it:

```bash
git rev-parse --abbrev-ref origin/HEAD   # e.g. origin/main
git fetch origin
git rebase origin/<default-branch>
```

Force-pushing a feature branch after a rebase is expected. Never force-push the default branch.

Commits should be good in themselves: one logical change each, building and passing on their own. No squashing before merge, unless the project's manifest opts into squash-merge.

Hooks run on every Git command, as the conduct rule requires. If a hook fails, fix the cause and rerun the hook and the affected checks before retrying.
