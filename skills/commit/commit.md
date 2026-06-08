---
name: commit
description: Create a well-formed git commit following team standards — atomic scope, imperative subject ≤50 chars, body explaining what/why, 72-char line wrap. Use when the user asks to commit, wants to write a commit message, or invokes /commit.
---

# Commit — Git Commit Standards

Create a well-formed git commit that follows the team's commit standards.

## Rules

- Subject line: imperative mood, ≤50 chars, no trailing period
- Separate subject and body with a blank line
- Body lines wrapped at ≤72 chars
- Body explains **what** changed and **why**, not how
- Reference issue IDs when available (e.g. `Related: #123`)
- One logical change per commit — do not mix unrelated concerns

**Exceptions:** typo/docs-only fixes may omit the body if intent is obvious from the subject alone.

## Steps

### 1. Check staged changes

Run these in parallel:

```bash
git diff --cached --stat
git diff --cached
```

If nothing is staged (`git diff --cached` is empty), check for unstaged changes:

```bash
git status --short
git diff --stat
```

If there are unstaged changes but nothing staged, ask the user which files to stage — do not stage everything automatically.

### 2. Assess commit scope

Review the diff to confirm it represents **one logical change**. If the staged changes span unrelated concerns (e.g. a bug fix mixed with a refactor mixed with a config tweak), flag this to the user and suggest splitting into separate commits before proceeding.

### 3. Draft the commit message

Using the diff and any context from the user, draft a message following this template:

```
<subject line — imperative, ≤50 chars, no period>

<body — what changed and why; wrap at 72 chars>

<optional: Related: #issue-id>
```

Good example:
```
Add authentication endpoint

Implement token-based authentication to secure API access.

Uses short-lived access credentials with secure refresh handling.
Improves session security while keeping client retry behavior predictable.

Related: #123
```


### 4. Validate the message

Before committing, verify:

- [ ] Subject is ≤50 chars
- [ ] Subject uses imperative mood (e.g. "Add", "Fix", "Remove", not "Added", "Fixes", "Removes")
- [ ] Subject has no trailing period
- [ ] Subject and body are separated by a blank line
- [ ] Body lines are ≤72 chars
- [ ] Body explains what/why (not just restates the subject)
- [ ] Issue reference included if available

If any check fails, revise before proceeding.

### 5. Execute the commit

Run the commit using a heredoc to preserve formatting:

```bash
git commit -m "$(cat <<'EOF'
<subject>

<body>

<references>
EOF
)"
```

Show the user the final commit hash and subject line to confirm success.
