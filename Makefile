UV ?= uv
RUN := $(UV) run --frozen

.PHONY: check check-fast lint format-check typecheck test test-npm dogfood docs

## check-fast: lint, format, types and the fast test suite; run while working
check-fast: lint format-check typecheck
	$(RUN) pytest -q -m "not slow"

## check: everything CI runs; run before handing over
check: lint format-check typecheck test test-npm dogfood

lint:
	$(RUN) ruff check .

format-check:
	$(RUN) ruff format --check .

typecheck:
	$(RUN) mypy

test:
	$(RUN) pytest -q

test-npm:
	node --test npm/test/*.test.js

## dogfood: this repository's own generated instructions match its content
dogfood:
	$(RUN) oees-agents check . --content-dir .

## docs: regenerate the tables in README.md and CONTRIBUTING.md from content/
docs:
	$(RUN) python -m oees_agents.docs .
