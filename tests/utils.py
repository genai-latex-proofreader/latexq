from pathlib import Path

from lq.main import cli


def run_lq_cli(*args: str) -> None:
    cli(args)


def assert_output_files(
    output_files: dict[Path, str], expected_files: dict[Path, str]
) -> None:
    assert set(output_files) == set(expected_files)
    for path in sorted(expected_files):
        assert output_files[path] == expected_files[path], (
            f"Mismatch in {path}:\n"
            f"actual={output_files[path]!r}\n"
            f"expected={expected_files[path]!r}"
        )
