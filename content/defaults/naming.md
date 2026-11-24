---
description: Inclusive technical terms and American English spelling in every identifier
---

# Naming

Default for OEES projects. A project opts out in its manifest. This rule covers the names in the code. The language conduct rule covers the prose.

## Use the inclusive term

Use the term that describes the thing:

- `allow-list` and `deny-list`, not `whitelist` or `blacklist`.
- `primary` and `replica` for a database or a queue, not `master` or `slave`.
- `main` for a default branch.
- `safety check` for a check that catches an impossible state.

Each replacement is the clearer word as well as the inclusive one. A deny-list says what it denies. A blacklist says nothing.

A term reaches the code through an external API, a legacy column or a vendor library. Keep it at that boundary. Map it to our term on the way in, and never carry it into a new name.

## Spell every identifier in American English

Use American English spelling in each name that an engineer types. This covers a variable, a function, a class, a file, a branch, an API field, a database column, an event name and a metric name. Write `color`, `serialize`, `license` and `behavior`.

One spelling across the group lets a search find every use. Two spellings for one concept hide half of them.

Exceptions: an identifier that an external system defines keeps the spelling of that system at the boundary.
