# `latexq` development

## Dev container

This repo is set up for dev-container development with all dependencies and tools required for `latexq` development.
To use this, one needs a laptop with Docker and VS Code installed.

- Clone the `latexq` repository and open the root in VS Code.
- Ensure that the VS Code Dev Containers plugin (id `ms-vscode-remote.remote-containers`) is installed.
- To build and open the devcontainer, press the green `><` symbol in the lower left corner of VS Code, and select "reopen in container".
- To install development dependencies:

```bash
$ uv sync --extra dev
```
- To test that everything is working correctly:
```bash
$ make test
$ make test-e2e
$ make pre-commit
```

This setup is tested in macOS.

Note: the dev container does not include a LaTeX installation.

## Make commands

The repo contains a makefile with common tasks to help development.
For a list of commands, run `make`:

```bash
$ make
Available commands:
  audit-check  - Security audit Python dependencies
  pre-commit   - Run pre-commit framework checks
  uv-sync      - Install dependencies
  uv-check     - Validate uv.lock is in sync and all hashes are correct
  package      - Build distribution packages in dist/
  test         - Run tests
  test-e2e     - Test latexq on some sample papers downloaded from arXiv
  ruff-check   - Check linting and formatting for src/ and tests/
  ruff-fix     - Auto-fix linting and formatting for src/ and tests/
  mypy-check   - Run mypy type checking
```

Many of these commands are run automatically in the CI pipeline.
