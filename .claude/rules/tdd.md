# Test-Driven Development

All behavioral changes follow Test-Driven Development. Tests come before implementation.

## Hard Requirements

- Write a failing test before the implementation.
- Follow red → green → refactor — in that order.
- No behavioral change ships without test coverage.
- Tests and implementation travel in the same commit.

## Workflow

1. **Red** — write a test that describes the desired behavior. Run it and confirm it fails for the right reason (not an import/syntax error).
2. **Green** — write the minimum code to make the test pass. No more.
3. **Refactor** — clean up while keeping tests green. Run the full suite after each change.

## What Requires a Test

These always need a test:

- New function, method, class, or component
- Changed return value or side effect
- Bug fix — write a test that reproduces the bug first, then fix it

These do not need a new test (but existing tests must still pass):

- Pure refactors with no behavior change
- Renaming, comments, documentation
- Config or environment changes

## Exception

Strict TDD may be skipped for urgent hotfixes **only when explicitly instructed**. When skipped, note the reason in the PR or commit.

## Examples

```python
# Write the test first
def test_create_task_sets_default_status():
    task = create_task(title="Buy milk")
    assert task.status == "pending"

# Run it — confirm it fails
# Then write the implementation
def create_task(title: str) -> Task:
    return Task(title=title, status="pending")
```

```typescript
// Write the test first
it('shows an error when title is empty', () => {
  render(<TaskForm onSubmit={jest.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: /submit/i }));
  expect(screen.getByText('Title is required')).toBeInTheDocument();
});

// Run it — confirm it fails
// Then implement the validation in TaskForm
```
