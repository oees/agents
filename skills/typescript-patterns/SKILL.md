---
name: typescript-patterns
description: How OEES builds TypeScript frontends — React + TypeScript + Vite with TanStack Query, strict types, schema validation at boundaries, feature-first layout. Use when writing or reviewing TypeScript or React code.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# TypeScript Patterns

Frontends are React + TypeScript + Vite with TanStack Query; server-rendered projects use HTMX + Alpine instead and do not need this skill. The project context says which. Work in the stack the project uses and do not add another framework, router or state library alongside it.

Why: one frontend stack means shared components, shared lint and type configuration, and engineers who can move between repos.

## What the frontend owns

UI, state orchestration and API calls. Business rules, permissions and computed outcomes (prices, KPIs, eligibility) come from the backend; the frontend displays them. Cosmetic derivation, such as formatting or sorting a list on screen, is fine.

## Type safety

`strict: true` in `tsconfig.json`. No `any`: use `unknown` and narrow. Avoid `as` casts; needing one usually means a boundary type is wrong. Any escape hatch carries a comment saying why.

## Validation at boundaries

Validate API responses and form input with a schema library and infer the static types from the schemas, so the runtime check and the type cannot drift. Inside the app, trust the static types; do not re-validate.

## State

```
What kind of state?
├── Server data (fetched, cached)   → TanStack Query
├── Form state                      → a form library wired to the same schemas
├── Shared UI state                 → Context or a small store
└── Local component state           → useState
```

Server data lives only in TanStack Query: one query key per resource, and every mutation invalidates the keys it affects, explicitly. Never copy server data into `useState` or a global store. Derive values instead of storing them.

## Async

Independent requests → `Promise.all`; results that may partly fail → `Promise.allSettled`. No floating promises: await them, or mark a deliberate fire-and-forget with `void` and handle its error. Handle errors at a boundary (the query's error state, an error boundary), not scattered through render code, and show the user a clear message rather than a raw error.

## Layout

Feature-first: a feature's components, hooks, types, API calls and tests live together. Code shared by several features lives in one shared module. No barrel files (`index.ts` re-exports) in large feature trees; they hide coupling and slow the bundler.

## Checklist

- [ ] The stack is the one the project context names
- [ ] `strict: true`, no `any`, no unexplained `as`
- [ ] API responses and forms validated with schemas; types inferred from them
- [ ] Server data in TanStack Query with explicit invalidation
- [ ] No floating promises; errors handled at a boundary
- [ ] No business rules in the browser
- [ ] Feature-first folders, no barrel files
