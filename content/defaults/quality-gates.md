---
description: Lint, format, types, tests and dependency scan before merge, run through make check and make check-fast
---

# Quality gates

Default for OEES projects. A project opts out in its manifest.

Before every merge, run lint, format, type checks, tests and a dependency vulnerability scan. Use the same commands locally and in CI. Never merge with a known failing check, unless a human has waived that specific check.

Every project has two commands. The project context names them. By default, they are:

- `make check-fast`: lint, format, types and the tests affected by the change. Run it while you work and before each commit.
- `make check`: everything that CI runs, including the full test suite and the dependency scan. Run it before you deliver the work.

For the backend, use a fast linter and formatter, a type checker and a dependency scanner. For the frontend, use lint, format and strict typing with no `any`. Prefer pre-commit hooks for local feedback.

Exceptions: a legacy module can use an ignore list only with an issue reference and an expiry date. Each typed escape hatch (`any`, `# type: ignore`) needs a justification comment.
