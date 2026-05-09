from pathlib import Path
from typing import cast

import pytest

from lq.utils.io import (
    DIRECT_PATH_ERROR_MESSAGE,
    DirectoryFileReader,
    InMemoryFileReader,
    ensure_path_exists,
    read_directory,
    resolve_path_within_base_dir,
    write_directory,
)

READER_TEST_FILES: dict[Path, bytes] = {
    Path("file1.txt"): b"content1",
    Path("subdir/file2.txt"): b"content2",
}


@pytest.fixture(params=["directory", "memory"])
def file_reader_case(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> tuple[DirectoryFileReader | InMemoryFileReader, dict[Path, bytes]]:
    if request.param == "directory":
        write_directory(READER_TEST_FILES, tmp_path)
        return DirectoryFileReader(tmp_path), READER_TEST_FILES

    return InMemoryFileReader(READER_TEST_FILES), READER_TEST_FILES


# --- test ensure_path_exists ---


def test_ensure_path_exists(tmp_path: Path):
    target_file = tmp_path / "foo" / "bar" / "test.txt"
    assert not target_file.parent.exists()

    returned_path = ensure_path_exists(target_file)
    assert target_file.parent.exists()
    assert target_file.parent.is_dir()
    assert returned_path is target_file

    ensure_path_exists(target_file)
    assert target_file.parent.exists()


# --- test directory io ---


def test_read_directory_empty_directory(tmp_path: Path):
    assert read_directory(tmp_path) == {}


def test_read_directory_reads_all_files(tmp_path: Path):
    expected_files = READER_TEST_FILES

    write_directory(expected_files, tmp_path)

    res = read_directory(tmp_path)
    assert res == expected_files


def test_file_reader_reads_existing_path(
    file_reader_case: tuple[
        DirectoryFileReader | InMemoryFileReader, dict[Path, bytes]
    ],
):
    file_reader, expected_files = file_reader_case

    assert (
        file_reader.read_bytes(Path("subdir/file2.txt"))
        == expected_files[Path("subdir/file2.txt")]
    )


def test_file_reader_rejects_absolute_paths(
    file_reader_case: tuple[
        DirectoryFileReader | InMemoryFileReader, dict[Path, bytes]
    ],
):
    file_reader, _ = file_reader_case

    with pytest.raises(ValueError, match="must be relative"):
        file_reader.read_bytes(Path("/tmp/file.txt"))


def test_file_reader_rejects_path_traversal(
    file_reader_case: tuple[
        DirectoryFileReader | InMemoryFileReader, dict[Path, bytes]
    ],
):
    file_reader, _ = file_reader_case

    with pytest.raises(ValueError, match=DIRECT_PATH_ERROR_MESSAGE):
        file_reader.read_bytes(Path("../outside.txt"))


def test_file_reader_lists_paths(
    file_reader_case: tuple[
        DirectoryFileReader | InMemoryFileReader, dict[Path, bytes]
    ],
):
    file_reader, expected_files = file_reader_case

    assert file_reader.list_paths() == tuple(sorted(expected_files.keys()))


def test_file_reader_rejects_missing_path(
    file_reader_case: tuple[
        DirectoryFileReader | InMemoryFileReader, dict[Path, bytes]
    ],
):
    file_reader, _ = file_reader_case

    with pytest.raises(FileNotFoundError):
        file_reader.read_bytes(Path("missing.txt"))


def test_in_memory_file_reader_rejects_paths_containing_dot_dot():
    file_reader = InMemoryFileReader(READER_TEST_FILES)

    with pytest.raises(ValueError, match=DIRECT_PATH_ERROR_MESSAGE):
        file_reader.read_bytes(Path("subdir/../file1.txt"))


def test_read_directory_rejects_symlink_outside_root(tmp_path: Path):
    outside_file = tmp_path.parent / "outside.txt"
    outside_file.write_bytes(b"outside")
    (tmp_path / "link.txt").symlink_to(outside_file)
    with pytest.raises(ValueError, match=DIRECT_PATH_ERROR_MESSAGE):
        read_directory(tmp_path)


# --- test write_directory ---


def test_write_directory_writes_nested_files(tmp_path: Path):
    expected_files: dict[Path, bytes] = {
        Path("foo.txt"): b"foo",
        Path("nested/bar.txt"): b"bar",
    }

    write_directory(expected_files, tmp_path)

    assert read_directory(tmp_path) == expected_files


def test_write_directory_writes_string_files(tmp_path: Path):
    write_directory({Path("file.txt"): "hello"}, tmp_path)

    assert (tmp_path / "file.txt").read_text() == "hello"


def test_write_directory_rejects_absolute_paths(tmp_path: Path):
    with pytest.raises(ValueError, match="must use relative paths"):
        write_directory(
            {
                Path("/etc/passwd"): b"bad",
            },
            tmp_path,
        )


def test_write_directory_rejects_path_traversal(tmp_path: Path):
    with pytest.raises(ValueError, match=DIRECT_PATH_ERROR_MESSAGE):
        write_directory({Path("../outside.txt"): b"bad"}, tmp_path)


def test_write_directory_rejects_non_bytes_or_string_content(tmp_path: Path):
    with pytest.raises(TypeError, match="must be bytes or str"):
        write_directory(
            cast(dict[Path, bytes | str], {Path("file.txt"): 123}), tmp_path
        )


# --- test resolve_path_within_base_dir ---


def test_resolve_path_within_base_dir_allows_nested_paths(tmp_path: Path):
    assert (
        resolve_path_within_base_dir(tmp_path, Path("nested/file.txt"))
        == (tmp_path / "nested/file.txt").resolve()
    )


def test_resolve_path_within_base_dir_rejects_path_traversal(tmp_path: Path):
    with pytest.raises(ValueError, match=DIRECT_PATH_ERROR_MESSAGE):
        resolve_path_within_base_dir(tmp_path, Path("../outside.txt"))
