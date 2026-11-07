---
description: Backend owns the truth, organise by domain, frontend orchestrates, validated deploys
---

# Standards

Default for OEES projects. A project opts out in its manifest.

## Backend owns the truth

Business rules, validation, authorisation, persistence and computed outcomes (prices, KPIs, billing) live in backend services and domain modules, never duplicated in clients.

## Organise by domain

Group code by business domain, not by technical layer. Files that change together live together. The project's kit sets the stack's layout, settings modules and test locations.

Exceptions: small utility repos may use simpler structure if boundaries stay clear. Monolithic modules are acceptable during migrations when a refactor plan is documented.

## Frontend orchestrates

Keep frontend code to UI, state orchestration and API consumption, with no backend business logic in components. Use strong static typing, schema-based input validation and a server-state cache with explicit invalidation. Cosmetic derivation on the client is fine.

Exceptions: prototypes may temporarily relax layering, but production must restore separation of concerns. Intentionally checked-in generated client code may include verbose types.

## Deployment

Run CI checks before every deployment and never deploy unvalidated changes to production. Keep configuration secure and specific to each environment.

Exceptions: emergency production fixes may bypass normal flow only with an identified approver, a documented incident severity, and a post-incident task to restore the CI/CD path.
