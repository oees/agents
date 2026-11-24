---
description: Every change reaches the default branch through a pull request, rebase-only merges, no merge commits, no squashing, commits that stand alone with a 70-character imperative subject
---

# Git

Default for OEES projects. A project opts out in its manifest. An opt-out changes only these instructions. The GitHub rules below still apply.

Every change reaches the default branch through a pull request. Never push to the default branch, not even a one-line fix. This also applies when your credentials can bypass the rules, as the credentials of an org owner can. If the project has a `staging` branch, follow the project's own instructions for it. Never force-push the `staging` branch.

Work on a short-lived branch. Detect the name of the default branch. Do not assume it. The project context names it, and Git reports it:

```bash
git rev-parse --abbrev-ref origin/HEAD   # e.g. origin/main
git fetch origin
git rebase origin/<default-branch>
```

To keep the branch current, rebase it onto the target branch. Never merge the target branch into it. After a rebase, you can force-push your own feature branch. Use `git push --force-with-lease` for this. Never force-push the default branch or rewrite its history.

Rebase and merge is the only merge method. Every OEES repository turns off merge commits and squash merges, with no exception for a project. Every commit lands on the default branch as you wrote it. So make each commit good in itself: one logical change that builds and passes on its own. Tidy the commits of the branch before review, not at merge time.

Express one thought in each commit. If the subject says "change this and that", split the commit. Commit a code movement separately from a code change. The move commit carries the import and reference updates that the move needs, and nothing else. Keep a refactor separate from a functional change.

Write the subject in the imperative mood, with a maximum of 70 characters. Start it with a capital letter. Use no final full stop. The subject must complete the sentence "If merged, this commit will...".

Put a blank line after the subject. Then write a body that says why the change is necessary and how it solves the problem. Wrap the body at 72 columns. Link the ticket.

Never credit a model with a `Co-Authored-By:` trailer. The author owns the work, and a model cannot be accountable for what ships. Add no model trailer of any kind.

A human reviews and merges the pull request. An agent never merges or approves a pull request. An agent never enables auto-merge.

Hooks run on every Git command, as the conduct rule requires. If a hook fails, fix the cause. Then rerun the hook and the affected checks before you try again.
