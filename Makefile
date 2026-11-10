# vectra developer commands. `make` alone lists them.
.DEFAULT_GOAL := help
ARGS ?= --help

.PHONY: help init check lint format format-fix typecheck imports test cov clean run install uninstall

help: ## List targets
	@awk -F':.*## ' '/^[a-z-]+:.*## /{printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

init: ## Create the venv and install dev dependencies
	uv sync

check: lint format typecheck imports cov ## Everything CI runs

lint: ## Ruff lint
	uv run ruff check .

format: ## Ruff format check
	uv run ruff format --check .

format-fix: ## Apply ruff format and safe fixes
	uv run ruff format . && uv run ruff check --fix .

typecheck: ## mypy --strict
	uv run mypy

imports: ## Layer contracts (import-linter)
	uv run lint-imports

test: ## Tests without coverage
	uv run pytest -q

cov: ## Tests with the coverage gate
	uv run pytest -q --cov --cov-report=term-missing

clean: ## Remove caches and build output
	rm -rf .mypy_cache .ruff_cache .pytest_cache .coverage htmlcov dist

run: ## Run vectra from the source tree: make run ARGS="skills list --json"
	uv run vectra $(ARGS)

install: ## Install `vectra` on your PATH (editable: source edits apply at once)
	uv tool install --force --editable .

uninstall: ## Remove the `vectra` command from your PATH
	uv tool uninstall vectra
