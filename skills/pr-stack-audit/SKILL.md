---
name: pr-stack-audit
description: Audit a stack of dependent pull requests, starting from a given PR and following each PR's children, and publish a report with the findings PR by PR. Use when the user asks to audit, review or check a PR stack, a chain of stacked PRs, or "the stack starting at #123".
---

> Calibrate every judgement call to the project context block in the instruction files. Where it is missing, ask before assuming anything about who depends on this code.

# PR Stack Audit

Audit a stack of pull requests, where each PR's base branch is the head branch of the one before it. Judge each PR on its own three-dot diff against its parent, then judge the stack as a whole. Publish the results as one report with a section per PR.

This is read-only. Do not push, rebase, comment, request reviews, approve or merge. Every fix goes in the report as a proposal.

## 1. Resolve the stack

The argument is the first PR to audit: a number, a URL or a branch name. With no argument, start from the PR for the current branch. If none is found, ask.

1. Read the starting PR: number, title, state, draft flag, base and head branches, head SHA.
2. Walk **up** the stack: find open PRs whose base branch is the current PR's head branch, and repeat from each one. If a stack tool is in use (Graphite `gt`, `ghstack`, `spr`, or stack links in PR descriptions), check its order against what you found and report any mismatch.
3. Walk **down** only to name the starting PR's parent, so its diff is measured correctly. Do not audit PRs below the starting point.
4. If a PR has more than one child, the stack branches. Audit every branch and show the result as a tree.
5. Before you audit anything, list the stack in order (number, title, base → head) and say how big it is. If it has more than 10 PRs, ask before going on.

Fetch every head branch. Measure each PR's diff from the merge-base with its parent PR's head (`git diff <parent-head>...<head>`), the three-dot diff GitHub shows. A two-dot diff against the parent tip shows the parent's newer commits as deletions in the child. Do not measure against the default branch: that repeats the stack beneath the PR. Only the bottom PR is measured from the merge-base with its own base.

## 2. Audit each PR

For each PR, bottom to top, collect evidence first and then judge it.

**Stack hygiene**
- The base branch is the parent's head branch, and the PR contains the parent's current tip (`git merge-base --is-ancestor`). If it does not, the PR is stale and needs a restack. Say so on its own. The three-dot diff leaves those missing parent commits out, so do not report them as changes the child made.
- Its three-dot diff against the parent holds only its own change, with none of the parent's commits repeated and nothing from a sibling.
- It does not depend on code that only arrives later in the stack.

**Scope and description**
- One logical change, small enough to review on its own. Name a split if it needs one.
- The title and description match the actual diff. The description says where it sits in the stack and what it depends on.

**Commits**
- Changes reach the default branch by rebase-and-merge, so every commit must stand on its own: one logical change that builds and passes alone. Flag fixup, WIP and "address review" commits, and commits that break and then fix something within the same PR.
- Commit messages follow the project's commit conventions.

**Correctness and quality**
- Review the diff for correctness, a test for each behaviour change, and security, plus any focus the diff calls for (migrations, infrastructure, UI).
- Gather these inputs before judging: the requirement and its authorised scope, the three-dot diff with its base and head, and the checks run on that head with their output. If one is missing, say so and review what you can. Do not invent the missing part. Read the whole diff, then enough surrounding code to judge it. Treat check output as evidence of only what those checks examine.
- If reviewer subagents are available, give each one a fresh context per PR with those inputs. They follow the `reviewing` skill, which is installed with them.
- Secrets or personal data in the diff, fixtures or description are always a Blocker.

**Review readiness**
- CI and required check status on the head SHA. Name each failing check.
- Review decision, unresolved review threads, mergeability, draft state.

Do not run the project's checks on each head unless the user asks for it. When they ask, run the fast checks named in the project context in a separate worktree per head, and report the result for each one.

## 3. Audit the stack as a whole

- Order: could the PRs land bottom to top with each one green? Flag any PR that only works once a later one has landed.
- Churn: code added in one PR and rewritten or removed later in the stack. Propose folding the change into the PR that introduced it.
- Split: does each boundary fall in a sensible place? Propose merging tiny PRs or splitting oversized ones.
- Migration order: a schema change ships before the code that needs it, as the migrations rule requires.

## 4. Report

Use these severity levels. Prefer a few high-conviction findings to a long list of cosmetic ones. Do not soften a blocker into a suggestion.

| Level | Meaning |
|---|---|
| **Blocker** | Must be fixed before acceptance: wrong behaviour, a security or data-loss risk, a broken requirement or a clear violation of a decided rule |
| **Major** | Should be fixed in this change: a structural regression, a missing case or safeguard, or a clear maintainability cost |
| **Minor** | Worth fixing if cheap |
| **Note** | An observation or question; no change required |

Structure:

1. **Summary**: the starting PR, the stack as an ordered list or a tree, a verdict for the stack (ready to land, ready after fixes, or needs rework), and finding counts by severity.
2. **Stack table**: one row per PR with number and title, base → head, size (+/−, files), CI, review state, stale or not, its worst severity and its verdict.
3. **One section per PR**, bottom to top: what it does in one or two sentences, then its findings. Each finding gives its severity, path and line, what is wrong and its consequence, and the fix you propose. End the section with the evidence you used and its gaps, such as checks that were not run or a diff too large to read in full.
4. **Stack-level findings** from step 3.
5. **Proposed next steps** in order: restacks, splits, fixes per PR. These are proposals, not actions you take.

Link every PR, file and line to its URL on the host. Use synthetic placeholders for any personal data instead of quoting it.

Publish the report as an artifact if your tool supports artifacts. Otherwise, write a self-contained HTML file (or Markdown if the user prefers) to a scratch location outside the repository and give its path. Never commit it. In chat, end with the stack verdict, the Blocker count and the link or path.

## Guardrails

- Read-only. No push, rebase, force-push, comment, review, label or merge, even when a fix is obvious. Offer a follow-up step, such as `/pr-tidy` for one PR, and wait for permission.
- Judge each PR on the three-dot diff against its parent (`git diff <parent-head>...<head>`). A two-dot diff against the parent tip turns the parent's newer commits into false deletions, and a diff against the default branch repeats the stack beneath the PR.
- If a PR cannot be fetched or its checks cannot be read, say so in its section. Never fill the gap with a guess.
- Never describe a check as passed unless you saw it pass on that head SHA.
