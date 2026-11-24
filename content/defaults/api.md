---
description: Versioned endpoints, consistent error envelopes, pagination, typed validation, token auth, generated docs, no client-inducible 500, external references, a permission check per identifier, stable error codes
---

# API design

Default for OEES projects. A project opts out in its manifest.

Version all endpoints under `/api/<version>/`. Return consistent error envelopes with appropriate HTTP status codes. Paginate all list endpoints. Use typed schema validation, token-based auth with secure refresh handling, and auto-generated API docs.

## No input causes a 500

A client must not be able to make the API return HTTP 500. A 500 is a defect in our code, and each one reaches the alert path for an engineer to fix.

Return a 4xx with the reason for each request that is malformed, incomplete, inconsistent or not permitted. Validate the whole input before the first side effect. Never let a parse error, a missing key, a wrong type or an absent record escape as an unhandled exception.

## Address a record by its external reference

Accept an `external_reference` in the request and return it in the response. Never use the primary key of the database.

A primary key is an implementation detail. It ties the contract to one table, it changes when the record moves between systems, and the number tells the caller how many rows exist.

## Check the permission on each identifier and on the relation

If a request names more than one record, check the permission of the viewer on each record. Then check the relation between the records.

A viewer who can read account A and can read meter M still has no right to read M as a part of A. Only the relation between A and M gives that right.

## Give the same answer for a hidden record and a missing one

Return the same error when the record does not exist and when the viewer cannot see it. A different status for each case tells the caller which references are real. That is data the viewer has no right to.

## Carry a stable error code

Put a machine-readable code in every error: `errorCode` in the extension of a GraphQL error, the code field of the REST envelope. The client reads the code and never the message.

Write the message for a developer who reads a log. Keep personal data out of it. Leave the wording for the user, and its translation, to the client. A message can change at any time. A code is part of the contract, so a change to a code is a breaking change.

Exceptions: a public endpoint can skip auth if its documentation says so and it has a rate limit. An internal-only endpoint can use a different auth pattern if it has a recorded security review.
