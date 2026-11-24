---
description: Backend owns the truth, organise by domain, frontend orchestrates, validated deploys
---

# Standards

Default for OEES projects. A project opts out in its manifest.

## Backend owns the truth

Business rules, validation, authorisation, persistence and computed outcomes (prices, KPIs, billing) live in backend services and domain modules. Never duplicate them in clients.

## Organise by domain

Group code by business domain, not by technical layer. Files that change together live together. The project's kit sets the stack's layout, settings modules and test locations.

Exceptions: a small utility repo can use a simpler structure if the boundaries stay clear. During a migration, a monolithic module is acceptable if a documented refactor plan exists.

## Frontend orchestrates

Keep frontend code to UI, state orchestration and API consumption, with no backend business logic in components. Use strong static typing, schema-based input validation and a server-state cache with explicit invalidation. Cosmetic derivation on the client is fine.

Exceptions: a prototype can relax the layering for a short time. Production code must restore the separation of concerns. Generated client code that you commit on purpose can include verbose types.

## Deployment

Run CI checks before every deployment. Never deploy unvalidated changes to production. Keep configuration secure and specific to each environment.

Exceptions: an emergency fix in production can bypass the normal flow only with three things. These are an identified approver, a documented incident severity and a task after the incident to restore the CI/CD path.
