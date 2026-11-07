SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := check
MAKEFLAGS += --warn-undefined-variables --no-builtin-rules

RUN := uv run --locked
# Narrow check-fast to the area you are changing: make check-fast TESTS=apps/billing
TESTS ?=

.PHONY: install format lint types test test-cov migrations-check audit check check-fast run worker migrate

# The gate always runs against the test settings, whatever .env selects for the dev server.
types test test-cov migrations-check check check-fast: export DJANGO_SETTINGS_MODULE := config.settings.test

install:
	uv sync --locked

format:
	$(RUN) ruff format .
	$(RUN) ruff check --fix .

lint:
	$(RUN) ruff check .
	$(RUN) ruff format --check .

types:
	$(RUN) mypy .

test:
	$(RUN) pytest $(TESTS)

test-cov:
	$(RUN) pytest --cov --cov-report=term-missing

migrations-check:
	$(RUN) python manage.py makemigrations --check --dry-run

audit:
	reqs="$$(mktemp)"; trap 'rm -f "$$reqs"' EXIT; \
	uv export --locked --no-dev --format requirements-txt --quiet --output-file "$$reqs"; \
	$(RUN) pip-audit --strict --disable-pip --requirement "$$reqs"

check: lint types test-cov migrations-check audit

check-fast: lint types
	$(RUN) pytest -m "not slow" -x -q $(TESTS)

run:
	$(RUN) python manage.py runserver 0.0.0.0:8000

worker:
	$(RUN) celery -A config worker --loglevel INFO

migrate:
	$(RUN) python manage.py migrate

# Kit and project fragments (make/*.mk) add prerequisites to the targets above, e.g.
# `check: lint-templates`. Last, so a fragment never becomes the default goal.
-include make/*.mk
