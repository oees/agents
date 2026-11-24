---
description: Structured logging, contextual errors, no silent exceptions
---

# Observability

Default for OEES projects. A project opts out in its manifest.

Emit structured logs for backend operations and failures, and for frontend failures. Include contextual identifiers (request and task IDs) in all log entries and error paths. Never swallow exceptions silently. Log each exception with context, then re-raise it or handle it explicitly. Redact sensitive fields from logs.

Use consistent log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) and one structured logger per service. Use consistent API error envelopes. Log a stack trace for each unexpected exception.

Exceptions: on high-frequency paths, you can sample debug logs when the volume affects cost or performance.
