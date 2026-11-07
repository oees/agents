---
description: Never commit secrets; use env vars and secret managers
---

# Secrets

Never commit credentials, tokens, API keys, private keys, or passwords to version control — including test files, comments, and example configs.

Use environment variables for runtime secrets. Keep `.env` files local and gitignored; commit only `.env.example` with placeholder values.

If a secret is accidentally committed: rotate it immediately, then scrub history. Deleting in a new commit is not enough.

Run `gitleaks` or equivalent in CI as a hard block. Treat scan failures as merge blockers.

Exceptions: non-sensitive config (feature flags, log levels, public URLs) may live in committed files when there is no security risk.
