---
name: plan
description: Write an implementation plan from a spec or requirements before touching code — one commit-sized task at a time, each naming its files and its failing test. Use when given a spec, a feature brief, or a multi-step task to plan out.
---

> Calibrate every judgement call to the project context block in the instruction files. Where it is missing, ask before assuming anything about who depends on this code.

# Writing Plans

A plan turns a spec into a sequence of commits someone else could carry out without you: an engineer or agent who knows the language but not this codebase or this domain. Say which files each task touches, which test fails first and what the commit is. Leave out what a competent engineer would do anyway.

**Save plans to** `docs/plans/YYYY-MM-DD-<feature-name>.md`, unless the project keeps them elsewhere.

## Scope

If the spec covers several independent subsystems, propose one plan per subsystem. Each plan should leave working, tested software behind on its own.

## Header

Every plan starts with:

```markdown
# <Feature name>

**Goal:** <one sentence: what this builds and for whom>

**Architecture:** <two or three sentences: the approach and the main moving parts>

**Tech stack:** <the languages, frameworks and libraries involved>

---
```

When the spec leaves decisions open, record the ones you took in a short table (topic, decision, who decided) after the header, so reviewers can veto them in one place.

## File map

Before the tasks, list the files that will be created or modified and what each is responsible for. This is where the design gets decided.

- One clear responsibility per file; files that change together live together.
- Follow the codebase's existing structure. Split a file you are changing only when it has grown unwieldy, and say so in the plan.

## Tasks

One task is one commit: a change that builds, passes its tests and makes sense on its own. Order tasks so every commit leaves the project working.

```markdown
### Task N: <what this commit achieves>

**Files:**
- Create: `exact/path/to/new_module.py`
- Modify: `exact/path/to/existing.py`
- Test: `exact/path/to/tests/test_module.py`

**Failing test first:** `test_rejects_reading_older_than_the_last_one` — <the behaviour it pins, in one line>.

<What to change, in prose. Name the functions, types, endpoints or settings involved.>

Commit: `<imperative subject line>`
```

- **Name the failing test** for every behavioural change before the implementation. Pure refactors, renames and configuration name the existing checks that must stay green instead.
- **Show code only where the shape is not obvious** from the description: a tricky signature, a data format, a migration sequence, a query. Do not write the whole implementation into the plan.
- **Exact paths and names.** Every file, function, type, command and setting is named exactly as it will appear.

## No placeholders

These are plan failures; never write them:

- "TBD", "TODO", "implement later", "fill in details"
- "add appropriate error handling", "add validation", "handle edge cases" without saying which
- "write tests for the above" without naming the tests
- "similar to Task N" (repeat what is needed; tasks may be read out of order)
- references to types, functions or files no task creates

## Self-review

When the plan is written, read the spec again and check the plan against it:

1. **Spec coverage:** point to the task that implements each requirement. Add a task for any gap.
2. **Placeholder scan:** search for the patterns above and fix them.
3. **Name consistency:** the names, signatures, paths and commands used in later tasks match the ones defined in earlier tasks.

Fix what you find inline, then hand the plan over.
