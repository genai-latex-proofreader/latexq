.PHONY: $(MAKECMDGOALS) help

SHELL := /bin/bash

help:
	@echo "Available commands:"
	@echo "  audit-check  - Security audit Python dependencies"
	@echo "  pre-commit   - Run pre-commit framework checks"
	@echo "  uv-sync      - Install dependencies"
	@echo "  uv-check     - Validate uv.lock is in sync and all hashes are correct"
	@echo "  package      - Build distribution packages in dist/"
	@echo "  test         - Run tests"
	@echo "  test-e2e     - Test latexq on some sample papers downloaded from arXiv"
	@echo "  ruff-check   - Check linting and formatting for src/ and tests/"
	@echo "  ruff-fix     - Auto-fix linting and formatting for src/ and tests/"
	@echo "  mypy-check   - Run mypy type checking"

pre-commit:
	uv run pre-commit run --all-files

uv-sync:
	@# This will install dependencies and update the lock file if dependencies have
	@# changed in pyproject.toml.
	uv sync --extra dev

uv-check:
	uv lock --check
	uv sync --locked --extra dev

package:
	uv build

test:
	uv run pytest \
	    --durations=5 \
	    --durations-min=1.0 \

test-e2e:
	uv run pytest \
	    -o addopts='' \
	    -m "e2e" \
	    --durations=5 \
	    --durations-min=1.0 \

audit-check:
	uv export --frozen --all-groups --format requirements.txt --no-emit-project \
		| uv run pip-audit --requirement /dev/stdin --disable-pip

ruff-check:
	uv run ruff check src tests
	uv run ruff format --check src tests

ruff-fix:
	uv run ruff check --fix src tests
	uv run ruff format src tests

mypy-check:
	uv run mypy
