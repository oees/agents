# Stacked PR Audit Fixes Implementation Plan

**Goal:** Remove the audited orchestration, migration, and generated-artifact
failures from PRs #4, #6, and #7 without touching the user's dirty `main`.

**Architecture:** Apply fixes from the bottom of the stack upward. Each PR gets
its own regression coverage and commit; downstream branches are rebased onto
the corrected parent before their own changes are made and force-pushed with a
lease.

**Tech Stack:** Bash, Markdown automation prompts, GitHub Actions, ShellCheck,
Gitleaks, Git.

---

### Task 1: Correct tier-3 role routing in PR #4

**Files:**
- Modify: `loops/tier-3-queue-driven-delivery.md`
- Modify: `scripts/check.sh`
- Modify: `.github/workflows/tooling-ci.yml`
- Modify: `scripts/install.sh`
- Modify: `scripts/uninstall.sh`
- Modify: `scripts/sync-cursor-rules.sh`

- [ ] **Step 1: Write failing prompt-contract checks**

Add checks proving that the coder may claim queue work without a build PR, an
approved human checkpoint is selectable by the merger, and the watchdog runs
without a merge candidate.

- [ ] **Step 2: Run the regression checks**

Run: `bash scripts/check.sh`

Expected: FAIL on the three contradictory tier-3 contracts.

- [ ] **Step 3: Make selection role-specific**

Replace the universal cheap exit with:

```text
CODER exits only when there is no build PR and no claimable queue capacity.
MERGER queries both stage:merge and approved stage:human PRs and always sweeps.
REQ-CHECKER and PR-CHECKER retain their stage-specific cheap exits.
```

- [ ] **Step 4: Enforce repository quality checks**

Fix existing ShellCheck findings and add CI steps equivalent to:

```yaml
- name: Lint shell scripts
  run: shellcheck scripts/*.sh
- name: Scan for secrets
  run: |
    go install github.com/gitleaks/gitleaks/v8@<pinned-version>
    "$(go env GOPATH)/bin/gitleaks" git --redact --no-banner
```

- [ ] **Step 5: Validate and commit**

Run:

```bash
bash scripts/check.sh
shellcheck scripts/*.sh
git diff --check
```

Expected: all commands pass.

Commit: `Fix tier-three role routing`

### Task 2: Harden generated exports in PR #6

**Files:**
- Modify: `scripts/check.sh`
- Modify: `scripts/sync-agents-md.sh`
- Modify: `scripts/sync-cursor-rules.sh`
- Regenerate: `.cursor/commands/*.md`

- [ ] **Step 1: Add a failing malformed-marker regression**

Seed an `AGENTS.md` with a begin marker but no end marker and assert that the
sync command fails without changing the file.

- [ ] **Step 2: Run the regression**

Run: `bash scripts/check.sh`

Expected: FAIL because content after the unmatched marker is currently lost.

- [ ] **Step 3: Validate marker pairs before writing**

Require exactly one begin marker, exactly one end marker, and begin-before-end.
On malformed input, print an error and exit non-zero without modifying the
target.

- [ ] **Step 4: Normalize generated command endings**

Generate each Cursor command with one final newline and no blank line at EOF.

- [ ] **Step 5: Validate and commit**

Run:

```bash
bash scripts/check.sh
shellcheck scripts/*.sh
git diff --check
```

Expected: all commands pass.

Commit: `Protect generated agent guidance`

### Task 3: Repair legacy migration in PR #7

**Files:**
- Modify: `scripts/check.sh`
- Modify: `scripts/init-repo.sh`

- [ ] **Step 1: Add a failing legacy-only migration regression**

Seed `.claude/CLAUDE.md` with only legacy `@rules/*.md` imports and assert that
bootstrap succeeds and leaves exactly `@../AGENTS.md`.

- [ ] **Step 2: Run the regression**

Run: `bash scripts/check.sh`

Expected: FAIL because `grep -v` exits one when it removes every line.

- [ ] **Step 3: Make empty migration output successful**

Replace the filtering pipeline with an `awk` filter that succeeds when all
legacy lines are removed, then atomically replace `CLAUDE.md`.

- [ ] **Step 4: Validate and commit**

Run:

```bash
bash scripts/check.sh
shellcheck scripts/*.sh
git diff --check
```

Expected: all commands pass.

Commit: `Fix legacy Claude rule migration`

### Task 4: Publish and verify the corrected stack

**Files:** none

- [ ] **Step 1: Push PR #4**

Run: `git push origin feat/tier-3-queue-driven-delivery`

- [ ] **Step 2: Rebase and push PR #6**

Run:

```bash
git rebase feat/tier-3-queue-driven-delivery
git push --force-with-lease origin feat/tri-tool-exports
```

- [ ] **Step 3: Rebase and push PR #7**

Run:

```bash
git rebase feat/tri-tool-exports
git push --force-with-lease origin feat/collapse-rules-into-agents-md
```

- [ ] **Step 4: Verify GitHub checks**

Run:

```bash
gh pr checks 4 --watch
gh pr checks 6 --watch
gh pr checks 7 --watch
```

Expected: every required check passes.
