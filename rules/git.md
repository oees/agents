---
description: Rebase-always git workflow, no merge commits, no squashing
---

# Git

Always rebase onto the target branch instead of merging. No merge commits on `main`.

```bash
git fetch origin
git rebase origin/main
```

Force-push to feature branches after a rebase is expected. Never force-push to `main`.

Commits should be good in themselves — no squashing before merge.
