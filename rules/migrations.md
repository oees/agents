---
description: Safe, backwards-compatible database schema migrations
---

# Migrations

Write migrations to be backwards-compatible: the app must run correctly against both old and new schema simultaneously. Never bundle a migration and the app code that requires it in the same deployment — ship the migration first, verify, then ship the app change.

Destructive operations (DROP COLUMN, DROP TABLE, renames) require a multi-step plan: deprecate → remove app references → deploy → then drop. Adding NOT NULL columns requires a default or backfill before applying the constraint.

Test against a copy of production data before merging. Write a `down` migration unless the operation is genuinely irreversible.

Exceptions: greenfield schemas with no live traffic may skip the backwards-compat constraint.
