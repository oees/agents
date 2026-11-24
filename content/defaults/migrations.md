---
description: Safe, backwards-compatible database schema migrations, each in its own pull request
---

# Migrations

Default for OEES projects. A project opts out in its manifest.

Write backwards-compatible migrations. The app must run correctly against the old schema and the new schema at the same time. Never put a migration and the app code that needs it in the same deployment. Ship the migration first and verify it. Then ship the app change.

Put the migration in a pull request of its own, with no application change in it. A schema change and a code change fail in different ways and recover in different ways. A revert of the code must not revert the schema. A pull request that holds only the migration also puts the generated SQL in front of the reviewer, instead of inside a feature diff.

A destructive operation (DROP COLUMN, DROP TABLE, rename) needs a plan in steps:

1. Deprecate the column, table or name.
2. Remove the references to it from the app.
3. Deploy.
4. Drop it.

If you add a NOT NULL column, give it a default or a backfill before you apply the constraint.

Test against a copy of production data before you merge. Write a `down` migration, unless nobody can reverse the operation.

Exceptions: a new schema with no live traffic can skip the backwards-compatibility constraint.
