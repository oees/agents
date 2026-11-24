---
description: A timeout on every call, one reused client, no synchronous retry, a vendor behind an abstraction with a fake and documented failure modes
---

# Integrations

Default for OEES projects. A project opts out in its manifest.

## Set a timeout on every call

Give every outbound call an explicit timeout. The default of a client library is often no timeout at all. One slow dependency then holds a worker until the request dies.

Set the connect timeout and the read timeout. Pick each one from the time that the caller can wait.

## Reuse one client

Build the HTTP client once and reuse it. A new client for each call opens a new TCP connection and a new TLS session. That costs more than the request itself.

Under concurrency, give the client a connection pool. Size the pool for the number of workers.

## Never retry inside the request

A failed call to another service gets no retry in the same request. A retry multiplies the load on a dependency that already fails, and the caller waits for each attempt.

Fail fast and return the error. Retry in a task, with a backoff.

## Put the vendor behind an abstraction

Depend on an interface that the domain owns, not on the client of the vendor. The types, errors and field names of the vendor stay in one adapter module.

- Ship a fake with every abstraction. The tests of the callers use the fake. They then reach no network and need no test mode from the vendor.
- Document each failure mode on the abstraction: the timeout, the rate limit, the partial success and the duplicate delivery. A caller cannot handle a failure that the interface hides.
- Keep the error types of the vendor out of the domain. Translate each one into an error that the domain defines.

Exceptions: a one-off script can call a vendor client directly. A vendor SDK that owns a whole protocol, such as a payment redirect flow, can show its own types in the tests of the adapter.
