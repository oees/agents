# Code Quality

Run lint, format, type checks, and tests before merge. Run security scans on backend dependencies. Never merge known failing lint or type checks without an explicit waiver.

Backend: fast linter, formatter, dependency scanner, type checks. Frontend: lint, format, strict typing, no `any`. Prefer pre-commit hooks for local feedback.

Exceptions: legacy modules may use ignore lists only with an issue reference and expiry date. Typed escape hatches (`any`, `# type: ignore`) require a justification comment.
