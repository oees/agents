---
name: shipped
description: Summarize everything the user has personally authored and shipped across all local git repositories in a configurable time period. Use when the user asks "what did I ship?", "what have I worked on?", or wants a personal activity summary.
---

# Shipped — Personal Git Activity Summary

Summarize everything the user has personally committed across all their local git repositories.

## Steps

### 1. Resolve the time period

If the user passed an argument (e.g. "last month", "last 2 weeks", "this week", "last sprint"), parse it into a `--since` date. Otherwise default to the last 7 days.

Convert relative periods to absolute dates using today's date. Examples:
- "last week" → `--since="7 days ago"`
- "last month" → `--since="1 month ago"`
- "last 2 weeks" → `--since="14 days ago"`
- "this week" → `--since="last Monday"`
- "last sprint" → `--since="14 days ago"` (assume 2-week sprints)

### 2. Get the user's git identity

Run both of these in parallel:
```
git config --global user.name
git config --global user.email
```

Use **both** name and email to identify the author — some repos may have different local configs. You'll pass `--author` using the email for precision.

### 3. Find all local git repositories

Run a single find command to locate all `.git` directories under `$HOME`, with a depth limit to avoid excessive recursion, and excluding noisy paths:

```bash
find "$HOME" -maxdepth 6 -name ".git" -type d \
  -not -path "*/node_modules/*" \
  -not -path "*/.cache/*" \
  -not -path "*/Library/*" \
  -not -path "*/.Trash/*" \
  -not -path "*/Applications/*" \
  -not -path "*/.npm/*" \
  -not -path "*/.rbenv/*" \
  -not -path "*/.pyenv/*" \
  -not -path "*/vendor/*" \
  2>/dev/null | sed 's|/.git$||'
```

### 4. Query commits per repository

For each repo, run:
```bash
git -C "<repo_path>" log --oneline --no-merges \
  --since="<resolved_date>" \
  --author="<user_email>" \
  2>/dev/null
```

If the email-based query returns nothing for a repo, retry with `--author="<user_name>"` — the repo may use a different email config.

Collect only repos that have at least one matching commit.

### 5. Write the summary

Group results by repository. For each repo with activity:
- Use the repo directory name as the heading
- Summarise what was shipped in plain language — focus on **what changed and why it matters**, not just commit message text
- Highlight releases, new features, bug fixes, and major refactors
- Merge related commits into coherent themes rather than listing each one

Lead with the most significant work. If there are many repos, call out the top 2–3 at the top before going into detail.

Keep it concise and readable — this is a personal shipping log, not a git log dump.
