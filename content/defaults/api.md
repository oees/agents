---
description: Versioned endpoints, consistent error envelopes, pagination, typed validation, token auth, generated docs
---

# API design

Default for OEES projects. A project opts out in its manifest.

Version all endpoints under `/api/<version>/`. Return consistent error envelopes with appropriate HTTP status codes. Paginate all list endpoints. Use typed schema validation, token-based auth with secure refresh handling, and auto-generated API docs.

Exceptions: a public endpoint can skip auth if its documentation says so and it has a rate limit. An internal-only endpoint can use a different auth pattern if it has a recorded security review.
