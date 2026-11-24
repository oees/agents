---
description: Structured logging, contextual errors, no silent exceptions, reverse-domain event names, explicit fields, units in field names, metrics for aggregates, Sentry for code defects
---

# Observability

Default for OEES projects. A project opts out in its manifest.

Emit structured logs for backend operations and failures, and for frontend failures. Include contextual identifiers (request and task IDs) in all log entries and error paths. Never swallow exceptions silently. Log each exception with context, then re-raise it or handle it explicitly. Redact sensitive fields from logs.

Use consistent log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) and one structured logger per service. Use consistent API error envelopes. Log a stack trace for each unexpected exception.

## Name the event after what happened

Name each event in reverse domain order, from the widest scope to the narrowest. Write `billing.invoice.issued`, not `issued_invoice`.

The name is a contract. A dashboard, a monitor and a search each depend on it. Keep the name stable, and rename it only together with its consumers.

## Write the fields that the reader needs

List every field explicitly. Never put an object, a dictionary or a serialized payload in the log and leave the reader to find the value.

- Put the unit in the field name: `duration_ms`, `amount_eur`, `size_bytes`. A field called `duration` tells the reader nothing.
- Identify the actor in a `viewer` field, in the format `{system}|{model}:{id}`, for example `kraken|account:A-1234ABCD`. One format across the services makes a search across them possible.
- Use the same field name for the same thing in every service.

## Count with metrics, not with logs

Use a metric for each value that you aggregate: a rate, a total or a percentile. Use a log for the detail of one occurrence. A count of log lines is slow and expensive, and the retention period deletes the answer.

Keep the cardinality of the tags bounded. Never use an identifier, a URL, an email address or a timestamp as a metric tag. Put those values in the log.

## Send to Sentry only what needs a code change

Sentry holds the defects that an engineer must fix. An expected failure is not a defect. A validation error, a missing record and a rate limit are expected failures. Report each one in the logs and the metrics, and keep it out of the alert path.

Exceptions: on high-frequency paths, you can sample debug logs when the volume affects cost or performance.
