# Observability

Emit structured logs for backend operations and failures as well as frontend failures. Include contextual identifiers (request/task IDs) in all log entries and error paths. Never swallow exceptions silently — log with context and re-raise or handle explicitly.

Use consistent log levels (DEBUG/INFO/WARNING/ERROR/CRITICAL), one structured logger per service, consistent API error envelopes, and stack traces for unexpected exceptions.

Exceptions: redact sensitive fields from logs; sample debug logs on high-frequency paths when volume impacts cost or performance.
