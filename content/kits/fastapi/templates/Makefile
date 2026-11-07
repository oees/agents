SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
MAKEFLAGS += --no-builtin-rules

RUN := uv run --locked
# Narrow `make check-fast` to the area you are changing: make check-fast TESTS=tests/core
TESTS ?= tests

export APP_ENV ?= local

.PHONY: help install format lint format-check typecheck test test-fast migration-check audit \
	check check-fast run migrate migration

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "%-16s %s\n", $$1, $$2}'

install: ## Install locked dependencies, dev tools included
	uv sync --locked

format: ## Fix formatting and autofixable lint
	$(RUN) ruff format .
	$(RUN) ruff check --fix .

lint: ## Lint
	$(RUN) ruff check .

format-check: ## Fail if anything is not formatted
	$(RUN) ruff format --check .

typecheck: ## mypy, strict
	$(RUN) mypy

test: ## Full test suite with the 80% coverage floor
	APP_ENV=test $(RUN) pytest --cov --cov-report=term-missing

test-fast: ## Tests not marked slow, stop at the first failure, no coverage
	APP_ENV=test $(RUN) pytest -m "not slow" -x -q $(TESTS)

migration-check: ## Migrations apply and match the models (alembic check) on the test database
	APP_ENV=test $(RUN) alembic upgrade head
	APP_ENV=test $(RUN) alembic check

audit: ## Known vulnerabilities in the locked dependencies
	uv export --locked --no-emit-project --format requirements-txt --quiet \
		| $(RUN) pip-audit --strict --disable-pip --require-hashes --requirement /dev/stdin

check: lint format-check typecheck test migration-check audit ## The full gate CI runs

check-fast: lint format-check typecheck test-fast ## The quick gate while working

run: ## Serve locally with reload (needs `docker compose up -d db`)
	$(RUN) uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log

migrate: ## Apply migrations to the database for APP_ENV
	$(RUN) alembic upgrade head

migration: ## Autogenerate a revision: make migration MESSAGE="add orders table"
	$(RUN) alembic revision --autogenerate -m "$(MESSAGE)"
