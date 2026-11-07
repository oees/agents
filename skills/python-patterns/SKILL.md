---
name: python-patterns
description: How OEES builds Python backends — Django + DRF or FastAPI, typed boundaries, domain exceptions, structured logging, settings per environment, imports at module top. Use when writing or reviewing Python code.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Python Patterns

What we do in Python at Octopus Energy España, and why. This skill holds what is true for every Python service; the kit skills (`django-drf`, `fastapi`) hold layout, settings modules, test layout and deploy detail for each stack.

## Framework

Backend services are Django + DRF for full-stack and admin-heavy products, FastAPI for API-only services and middleware. The project context says which; do not ask unless it is missing. Work in the framework the project uses and do not add a second one.

Why: one answer per kind of service lets engineers move between repos and lets the kits encode the details once.

## Async vs sync

I/O-bound work (database, HTTP, files) in an async service → `async def` with async drivers end to end. CPU-bound work → `def`, moved to a worker when it is slow. Never call a blocking library from async code on the event loop. Django views stay sync unless the project has chosen async views.

## Types and boundaries

Type parameters, return values, class attributes and every public function. Skip obvious locals. Code passes the project's type checker; a `# type: ignore[code]` needs a comment saying why.

Validate everything that crosses a boundary: Pydantic models in FastAPI, serializers in DRF, Pydantic settings for configuration, and explicit schemas for queue messages and third-party payloads. Inside the service, pass typed objects (models, dataclasses) and trust them; do not re-validate or pass loose dicts.

## Imports

Imports go at the top of the module. An import inside a function, class body or annotation is allowed only to break a documented circular dependency, with a comment saying so. Use an `if TYPE_CHECKING:` block for imports needed only by type hints.

Why: the top of the file then lists every dependency, and a broken import fails at startup rather than in the middle of a request.

## Layout

Organise by domain, one Django app or package per domain, not by technical layer. Files that change together live together. Business logic lives in services; views and endpoints validate input, call a service and shape the response; read queries live in query functions or managers. Follow the kit for where tests go.

## Settings

Split settings by environment: `base`, `local`, `test`, `production`, plus `staging` only where the project has one. Environment-specific values and every secret come from environment variables. Settings files hold no secrets.

## Errors

Services raise domain exceptions (`InvoiceAlreadyIssued`, not `ValueError`). One place translates them to HTTP responses (a DRF exception handler, FastAPI exception handlers) using the project's error envelope: an error code, a human-readable message and field-level details. Clients never see a stack trace. Never swallow an exception: log it with context and re-raise, or handle it explicitly.

## Logging

One structured logger per service: structlog, or the standard library configured for JSON. Log events with fields, not sentences: `logger.info("invoice_issued", invoice_id=invoice.id)`. Bind the request or task id once so every line carries it. Never log PII, tokens or secrets.

## Queries and transactions

Avoid N+1 queries: `select_related` and `prefetch_related` in Django, `selectinload` and `joinedload` in SQLAlchemy. Writes that belong together run in one transaction, and work that must follow a commit (enqueueing a task, sending an email) runs after it, through `transaction.on_commit` or an outbox.

## Background work

Persistent queues, retries, schedules and anything that must survive a restart go to Celery. FastAPI's `BackgroundTasks` only for in-process work that may be lost. Tasks are idempotent and take ids, not model instances.

## Checklist

- [ ] The framework is the one the project context names
- [ ] Async or sync matches the workload
- [ ] Input validated at the boundary, typed objects inside
- [ ] Business logic in services, reads in query functions
- [ ] No N+1 queries; related writes in one transaction
- [ ] Domain exceptions translated in one place; nothing swallowed
- [ ] Structured logs with request or task ids and no PII
- [ ] Imports at the top of the module
- [ ] Settings split `base/local/test/production`; secrets from the environment
