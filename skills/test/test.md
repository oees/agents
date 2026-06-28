---
name: test
description: Write well-structured tests following TDD. Test design, mocking discipline, naming, and coverage decisions. Use when writing tests or reviewing test quality.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Writing Tests

Principles for writing tests that catch real bugs and stay maintainable. Follows the TDD rule: failing test first, then implementation.

## What to Test

Test behavior and contracts, not implementation details. Test the public interface — if you need to break encapsulation to assert something, that's a design smell, not a test gap.

One test per logical behavior. If a test needs a long comment to explain what it's checking, split it.

## Naming

Names read as specs: `returns_empty_list_when_no_results`, `raises_when_user_not_found`. Not `test_function_1` or `test_happy_path`.

## Structure

Arrange / Act / Assert — in that order, with a blank line between each. Keep the Act section to one call. If setup is complex, extract a factory or fixture.

## Mocking Discipline

Mock at system boundaries only: HTTP, database, filesystem, time, randomness. Do not mock internal collaborators — that ties tests to implementation and lets real integration bugs through.

```
What should I mock?
├── External HTTP / third-party API   → mock
├── Database                          → real DB in integration tests, mock in unit tests
├── Filesystem / clock / randomness   → mock
└── Internal functions / services     → don't mock — test through them
```

## What Level to Test

```
What are you testing?
├── Pure logic / computation          → unit test
├── Service + DB interaction          → integration test
├── Bug fix                           → regression test first, then fix
└── Full user-facing flow             → e2e (sparingly)
```

Prefer integration tests over heavily-mocked unit tests for service-layer code. A test that hits a real DB is slower but far more trustworthy.

## Edge Cases

Before marking a test suite complete, check:
- [ ] Empty / null / undefined inputs
- [ ] Boundary values (zero, max, off-by-one)
- [ ] Error paths and exception handling
- [ ] Concurrent or repeated calls where relevant

## Parameterization

Use parameterized tests when the same logic runs over multiple inputs. Don't use them when different inputs test meaningfully different behaviors — those deserve separate named tests with clear intent.

## Decision Checklist

- [ ] Test written before implementation (TDD rule)?
- [ ] Testing behavior, not implementation details?
- [ ] Name reads as a spec sentence?
- [ ] Mocks only at system boundaries?
- [ ] Edge cases covered?
- [ ] Test passes for the right reason (would it fail if the behavior broke)?
