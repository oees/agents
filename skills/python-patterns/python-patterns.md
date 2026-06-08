---
name: python-patterns
description: Python development principles and decision-making. Framework selection, async patterns, type hints, project structure. Teaches thinking, not copying.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Python Patterns

Decision-making principles for Python. **Ask the user about framework preference when unclear. Never default to the same framework every time.**

## Framework Selection

```
What are you building?
├── API-first / Microservices   → FastAPI
├── Full-stack / CMS / Admin    → Django
├── Simple / Script / Learning  → Flask
├── AI/ML API serving           → FastAPI
└── Background workers          → Celery + any framework
```

Ask before choosing:
1. API-only or full-stack?
2. Need admin interface?
3. Team familiar with async?
4. Existing infrastructure?

## Async vs Sync

I/O-bound (database, HTTP, file) → `async def`. CPU-bound → `def` + multiprocessing.

Don't mix sync libraries into async code. Don't force async for CPU work.

## Type Hints

Always type function parameters, return types, class attributes, and public APIs. Skip local variables and one-off scripts.

Use Pydantic for API request/response models, config, and validation — not for internal data structures.

## Project Structure

Organise by domain responsibility, not technical layer. Files that change together live together. Keep tests in per-app `tests/` directories. Split settings by environment (base/local/staging/production).

## Background Tasks

- In-process, fire-and-forget, no persistence needed → FastAPI `BackgroundTasks`
- Long-running, retry logic, distributed workers, persistent queue → Celery or ARQ

## Error Handling

Raise domain exceptions in services. Catch and transform in handlers. Return consistent error envelopes with error code, human-readable message, and field-level details. Never expose stack traces to clients.

## Decision Checklist

Before implementing, confirm:
- [ ] Framework chosen for this context (not just the default)?
- [ ] Async vs sync decided based on workload type?
- [ ] Business logic in services, not routes/views?
- [ ] N+1 queries avoided (select_related / prefetch_related)?
- [ ] Background task approach chosen?
- [ ] Error handling pattern defined?
