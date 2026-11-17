---
description: Every change reaches the default branch through a pull request, rebase-only merges, no merge commits, no squashing, commits that stand alone
---

# Git

Default for OEES projects. A project opts out in its manifest. Opting out changes only these instructions; the GitHub rules below still apply.

Every change reaches the default branch through a pull request. Never push to the default branch, not even a one-line fix, and not even when your credentials could bypass the rules (an org owner's can). If the project has a `staging` branch, follow the project's own instructions for it; never force-push it.

Work on a short-lived branch. Detect the default branch rather than assuming its name; the project context names it, and Git reports it:

```bash
git rev-parse --abbrev-ref origin/HEAD   # e.g. origin/main
git fetch origin
git rebase origin/<default-branch>
```

Keep the branch up to date by rebasing it onto the target branch. Never merge the target branch into it. Force-pushing your own feature branch after a rebase is expected; use `git push --force-with-lease`. Never force-push the default branch or rewrite its history.

Rebase and merge is the only merge method. Merge commits and squash merges are turned off in every OEES repository, with no per-project exception. Every commit lands on the default branch as written, so each one must be good in itself: one logical change, building and passing on its own. Clean up the branch's commits before review, not at merge time.

A human reviews and merges the pull request. An agent never merges or approves a pull request and never turns on auto-merge.

Hooks run on every Git command, as the conduct rule requires. If a hook fails, fix the cause and rerun the hook and the affected checks before retrying.
