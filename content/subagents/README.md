# Subagents

A standard roster of Claude Code subagents for test-first, reviewed delivery. The main session orchestrates. Each subagent does one step in a fresh context, with only the tools and paths that step needs. The definitions hold no project-specific detail: each project supplies its commands, stack and audience through the project context block in its instruction files, its kit skills and its own conventions.

## Roster

`core/` is installed by default. `extended/` adds specialists for projects that need them.

| Subagent | Tier | Step | Job | Tools | Use for |
|---|---|---|---|---|---|
| `test-writer` | core | Red | Derive acceptance cases from the requirement and write failing tests before any implementation | Edit + Bash | Every behavioural change or bug fix |
| `implementer` | core | Green | Make the failing tests pass in the assigned paths, backend or UI, following the preloaded kit skills | Edit + Bash | Every code change |
| `simplifier` | core | Simplify | Simplify the green change without changing behaviour, applying the preloaded `code-review` skill | Edit + Bash | Every code change |
| `functional-reviewer` | core | Review | Does the change do what the requirement says, no less, no more? | Read-only | Every behavioural change |
| `engineering-reviewer` | core | Review | Maintainability, through the preloaded `code-review` skill, plus boundaries, layering, atomicity, errors, logs and tests | Read-only | Every code change |
| `security-reviewer` | core | Review | Authn, authz, PII, secrets, endpoints, uploads, dependencies, workflows, agent protections | Read-only | Changes in that scope |
| `migration-reviewer` | extended | Review | Backwards compatibility, locking, backfills, reversibility, rollout order | Read-only | Migrations, data imports, destructive data operations |
| `infra-implementer` | extended | Build | Write infrastructure, CI, container and tooling code. Never applies; prepares commands for a human | Edit + Bash | Infra, CI, Dockerfile, Makefile, tool config |
| `infra-reviewer` | extended | Review | Plans, deploy path, secrets and state, workflows, container image | Read-only | Infra, CI and deployment changes |
| `ui-reviewer` | extended | Review | Interaction pattern, CSP, styling, components, accessibility, translations | Read-only | UI changes |
| `documentation-writer` | extended | Write | Change docs in the owning file without changing meaning; draft requirement records | Edit + Bash | Every docs change |
| `docs-verifier` | extended | Review | Did the docs change keep its meaning, ownership and links? | Read-only | Docs changes beyond a typo |

Reviewers and the docs verifier preload the shared [`reviewing`](../../skills/reviewing/SKILL.md) skill: inputs, read-only working, severity levels (blocker, major, minor, note) and the findings report. The `simplifier` and `engineering-reviewer` preload [`code-review`](../../skills/code-review/SKILL.md), so the maintainability bar has one source.

## How they work together

1. **Understand.** The orchestrator reads the requirement and code, lists the acceptance cases and agrees the scope with the driver (the human directing the task).
2. **Red.** `test-writer` writes failing tests. The orchestrator runs them and checks they fail on an assertion or a deliberately unimplemented interface, not on an import or setup error.
3. **Green.** One `implementer` per set of paths makes the tests pass; several run in parallel only when their paths do not overlap. The orchestrator runs the checks itself.
4. **Docs.** `documentation-writer`, where installed, updates any docs the change makes stale.
5. **Simplify.** `simplifier` gets the requirement, paths and diff range, but not the implementers' reasoning. Run the checks again.
6. **Review.** Every reviewer the routing table selects runs in parallel. Reviewers cannot run commands, so give each one the requirement, the diff with its base and head, and the check output.
7. **Fix.** Send each blocker and major to the agent that owns it, then re-review with fresh reviewers.
8. **Hand over.** Report what changed, the evidence and the remaining gaps. A human accepts and merges.

| The change touches | Reviewer |
|---|---|
| Any behaviour | `functional-reviewer` |
| Any code | `engineering-reviewer` |
| Authentication, permissions, security settings, PII or its logging, uploads, dependencies, workflows, agent configuration, instruction files | `security-reviewer` |
| Migrations, data-import code, destructive data operations | `migration-reviewer` |
| Infrastructure, workflows, Dockerfile, Makefile, tool configuration | `infra-reviewer` |
| Templates, components, static assets, views that render them | `ui-reviewer` |
| Docs and root Markdown | `docs-verifier` |

Without the extended tier, the `engineering-reviewer` and `security-reviewer` cover those areas as best they can, and the hand-over says which specialist review did not run.

The invariants that make this work:

- The test-writer and implementers run in separate contexts, so tests come from the requirement, not the implementation.
- Implementers never change the test-writer's expectations. Changing one needs a human-reviewed rationale.
- Reviewers are read-only and arrive without the authors' reasoning.
- The docs verifier never verifies a change it wrote.
- Agent reviews assist the human. They never count as human approval.

## Adopting in a project

1. Copy `core/*.md`, and the `extended/*.md` the project wants, into `.claude/agents/`. Copy `skills/reviewing/` and `skills/code-review/` into `.claude/skills/`.
2. Make sure the project context block in `AGENTS.md` or `CLAUDE.md` names the stack and the check commands (the targeted test command, the fast checks and the full checks). In the project's own instructions, also name:
   - **Protected changes:** which changes are routine, which are sensitive and need the scope confirmed first (auth, security settings, PII, migrations, data imports, dependencies, infrastructure), and which need explicit authorisation and human review (CI, check configuration, hooks, agent configuration, instruction files, CODEOWNERS).
   - **Requirements:** where accepted requirements live, such as specs, tickets or a requirements record.
   - **Docs conventions:** owning files, decision labels, the link check.
3. Add the project's kit and pattern skills to each agent's `skills:` list, for example a Python kit on `implementer`, `simplifier` and the engineering, migration and security reviewers, and a UI kit on `implementer` and `ui-reviewer`. The agents follow whatever is preloaded.
4. Optionally, enforce the write scopes with a `PreToolUse` hook on the file-editing tools.
