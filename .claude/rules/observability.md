# Observability, Safety, and Stability

All code must prioritize observability, safety, and stability.

## Hard Requirements

- Do: emit structured logs for backend operations and failures.
- Do: include contextual identifiers in logs and error paths.
- Do not: swallow exceptions silently.
- Why: observable failures are faster to diagnose and safer to recover from.

## Opinionated Defaults

- Use consistent log levels (DEBUG/INFO/WARNING/ERROR/CRITICAL).
- Prefer one consistent structured logger across backend services.
- Return consistent API error envelopes.
- Include stack traces for unexpected exceptions.

## Exceptions

- Highly sensitive fields may be redacted or omitted from logs.
- High-frequency paths can sample debug logs when volume impacts cost/perf.

## Acceptance Checks

- Errors are logged with enough context to correlate request/task scope.
- Critical failures include stack trace or equivalent diagnostic context.
- API error format is consistent across modules.

## Examples

```python
# ✅ GOOD
import logging

logger = logging.getLogger(__name__)

try:
    result = process_task(task_id)
    logger.info("Task processed successfully", extra={"task_id": task_id})
except Exception:
    logger.exception("Task processing failed", extra={"task_id": task_id})
    raise
```

```typescript
// ✅ GOOD
try {
  await api.createTask(data);
} catch (error) {
  logger.error('Failed to create task', { error, data });
  throw new TaskCreationError('Unable to create task', { cause: error });
}
```
