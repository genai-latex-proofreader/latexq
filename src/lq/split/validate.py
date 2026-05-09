import sys
from collections.abc import Mapping
from pathlib import Path

from lq.split.command import _generate_split_output
from lq.split.data_model import SplitConfig
from lq.utils.io import DirectoryFileReader


def _path_is_split_managed_tex(
    path: Path,
    main_file: Path,
    config: SplitConfig,
) -> bool:
    if path == main_file:
        return True

    if path.suffix != ".tex":
        return False

    main_sections_dir = Path(config.main_sections_dir)
    appendix_sections_dir = Path(config.appendix_sections_dir)
    return path.is_relative_to(main_sections_dir) or path.is_relative_to(
        appendix_sections_dir
    )


def _to_bytes(content: bytes | str) -> bytes:
    if isinstance(content, str):
        return content.encode("utf-8")
    return content


def _get_split_managed_tex_files(
    files: Mapping[Path, bytes | str],
    main_file: Path,
    config: SplitConfig,
) -> dict[Path, bytes]:
    return {
        path: _to_bytes(content)
        for path, content in files.items()
        if _path_is_split_managed_tex(path, main_file, config)
    }


def _generate_validation_warnings(
    actual_files: dict[Path, bytes],
    expected_files: dict[Path, bytes],
) -> list[str]:
    warnings: list[str] = []
    remaining_actual = dict(actual_files)
    remaining_expected = dict(expected_files)

    exact_match_paths = sorted(
        {
            path
            for path in remaining_actual.keys() & remaining_expected.keys()
            if remaining_actual[path] == remaining_expected[path]
        },
        key=str,
    )
    for path in exact_match_paths:
        del remaining_actual[path]
        del remaining_expected[path]

    content_drift_paths = sorted(
        remaining_actual.keys() & remaining_expected.keys(),
        key=str,
    )
    for path in content_drift_paths:
        warnings.append(f"content drift: {path}")
        del remaining_actual[path]
        del remaining_expected[path]

    actual_by_content: dict[bytes, list[Path]] = {}
    for path, content in remaining_actual.items():
        actual_by_content.setdefault(content, []).append(path)

    expected_by_content: dict[bytes, list[Path]] = {}
    for path, content in remaining_expected.items():
        expected_by_content.setdefault(content, []).append(path)

    shared_contents = [
        content for content in actual_by_content if content in expected_by_content
    ]
    for content in shared_contents:
        actual_paths = sorted(actual_by_content[content], key=str)
        expected_paths = sorted(expected_by_content[content], key=str)
        pair_count = min(len(actual_paths), len(expected_paths))
        for index in range(pair_count):
            actual_path = actual_paths[index]
            expected_path = expected_paths[index]
            warnings.append(
                f"path drift: actual {actual_path} expected {expected_path}"
            )
            del remaining_actual[actual_path]
            del remaining_expected[expected_path]

    for path in sorted(remaining_actual, key=str):
        warnings.append(f"orphan file: {path}")

    for path in sorted(remaining_expected, key=str):
        warnings.append(f"missing file: {path}")

    return warnings


def validate_split_command(
    input_file: Path,
    config_file: Path,
) -> None:
    input_path, split_config, expected_output = _generate_split_output(
        input_file,
        config_file,
    )
    file_reader = DirectoryFileReader(input_path.parent)
    main_file = Path(input_path.name)
    warnings = _generate_validation_warnings(
        actual_files={
            path: file_reader.read_bytes(path)
            for path in file_reader.list_paths()
            if _path_is_split_managed_tex(path, main_file, split_config)
        },
        expected_files=_get_split_managed_tex_files(
            expected_output,
            main_file,
            split_config,
        ),
    )
    if warnings:
        for warning in warnings:
            print(warning, file=sys.stderr)
        sys.exit(1)
