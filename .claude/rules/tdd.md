# TDD

Write a failing test before every behavioral change. Red → green → refactor, in that order. Tests ship in the same commit as the implementation.

Requires a test: new functions/classes/components, changed return values or side effects, bug fixes (reproduce the bug with a test first, then fix).
No new test needed: pure refactors, renames, comments, config changes — but existing tests must still pass.

Exception: skip only for urgent hotfixes when explicitly instructed; note the reason in the commit.
