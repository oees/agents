---
description: Never commit secrets; keep runtime secrets in environment variables
---

# Secrets

Never commit credentials, tokens, API keys, private keys or passwords to version control. This rule also applies to test files, comments and example configs.

Use environment variables for runtime secrets. Keep `.env` files local and gitignored. Commit only `.env.example`, with placeholder values.

If you commit a secret by accident, rotate it immediately. Then scrub it from the history. A new commit that deletes the secret is not enough.

Run `gitleaks` or an equivalent scanner in CI as a hard block. Treat a scan failure as a merge blocker.

Exceptions: non-sensitive config (feature flags, log levels, public URLs) can stay in committed files when there is no security risk.
