---
name: typescript-patterns
description: TypeScript/React frontend principles and decision-making. Framework selection, async patterns, type safety, state management. Teaches thinking, not copying.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# TypeScript Patterns

Decision-making principles for TypeScript frontends. **Ask about framework preference when unclear. Never default to the same framework every time.**

## Framework Selection

```
What are you building?
├── Content-heavy / marketing    → Next.js (SSG/ISR)
├── Full-stack / server-heavy    → Next.js or Remix
└── SPA / no SSR needed          → Vite + React
```

Ask before choosing:
1. SSR needed, or SPA is fine?
2. Server components or client-only?
3. Existing infra constraints?

## Type Safety

Enable `strict: true` in tsconfig. No `any` — use `unknown` with narrowing instead. Avoid `as` casts; if one is needed, the type boundary is likely wrong.

Validate at API and form boundaries with a schema library. Internal data structures don't need runtime validation — trust static types there.

## Async Patterns

Independent work → `Promise.all`. Results that can partially fail → `Promise.allSettled`. Never leave floating promises — unawaited calls must be explicitly fire-and-forget with error handling.

Propagate errors up to the nearest boundary rather than swallowing them. `try/catch` at handler or error boundary level, not scattered through render paths.

## State Management

```
What kind of state?
├── Server data (fetched/cached)  → server-state library
├── Form state                    → form library
├── Shared UI state               → lightweight store or Context
└── Local component state         → useState
```

Don't use `useState` for server data — it duplicates cache management. Don't use a global store for server data — that's what a server-state library is for.

## Project Structure

Organise by feature/domain, not by technical layer. Components, hooks, types, and tests for a feature live together. Shared utilities live in a dedicated shared module.

Avoid barrel files (`index.ts` re-exports) in large feature trees — they create hidden coupling and slow bundlers.

## Decision Checklist

Before implementing, confirm:
- [ ] Framework chosen for this context?
- [ ] `strict: true` in tsconfig?
- [ ] Runtime validation at API and form boundaries?
- [ ] Server data in a server-state library, not `useState`?
- [ ] No floating promises?
- [ ] No `any` or unjustified `as` casts?
- [ ] Feature-first folder structure?
