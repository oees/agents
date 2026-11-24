---
description: Personal data stays out of logs, traces, errors, fixtures and prompts
---

# Data protection

Personal data is any value that identifies a person, alone or together with another value. Examples are name, email, phone, address, DNI/NIE, IBAN, CUPS and meter serial, geolocation, and consumption tied to a supply point. Log the surrogate id (account, supply, request, task) instead.

Never write personal data to a sink that outlives the request. Each of these is such a sink:

- logs, log context, traces, span attributes and metric labels
- exception messages, URLs, cache keys and queue arguments
- analytics events, alerts and tickets
- prompts sent to a model or an external API

Redact personal data at one boundary per service, not at each call site. Prove the redaction with a test. The test sends a known value through the real pipeline and asserts that the value never reaches the sink. An untested convention is not a safeguard.

Serializers, exports and outbound payloads carry only the fields that the caller needs. Fixtures, docs, screenshots and agent prompts use synthetic or approved anonymised data. Every store that holds personal data needs a retention period and an erasure path that reaches the store.

A leak is an incident. If personal data leaks, do these steps:

1. Tell the data protection officer (dpd@octopusenergy.es) the same day.
2. Purge the sink.
3. Close the path.

A later commit that deletes the line is not enough.

Exceptions: the system of record stores what its lawful basis allows. The UI shows that data to an authorised user. If you debug with real data, you need a named approver, an access-controlled destination and a deletion deadline.
