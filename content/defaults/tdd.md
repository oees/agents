---
description: "TDD: write failing tests before implementation, red-green-refactor"
---

# TDD

Default for OEES projects. A project opts out in its manifest.

Write a failing test before every behavioural change. Do the steps red, green and refactor, in that order. Ship the tests in the same commit as the implementation.

These changes need a test:

- a new function, class or component
- a changed return value or side effect
- a bug fix: first reproduce the bug with a test, then fix it

These changes need no new test, but the existing tests must still pass:

- pure refactors and renames
- comments
- config changes

Exception: skip the test only for an urgent hotfix, and only when a human explicitly tells you to. Write the reason in the commit.
