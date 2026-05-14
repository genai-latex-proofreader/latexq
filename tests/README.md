# Tests for latexq

Tests are divided by intent:

- `tests/unit`: implementation-focused tests for internal components.
- `tests/acceptance`: behavior-level tests for end-to-end workflows and features.
- `tests/usage_docs`: executable checks to validate concrete command examples in the usage docs under `docs/`.
- `tests/e2e`: test latexq on some sample papers downloaded from arXiv.

Test fixtures are local to each test file.

Note:
Repository licensing is defined in [LICENSE.md](../LICENSE.md).
The tests in `tests/e2e` may download third-party arXiv papers at runtime;
those downloaded materials are not covered by the repository license and remain subject to their original copyright and licensing terms.
