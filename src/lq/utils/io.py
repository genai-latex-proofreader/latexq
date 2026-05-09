from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

DIRECT_PATH_ERROR_MESSAGE = "Paths must be direct; they must not include '..' or resolve outside the base directory."


class FileReader(Protocol):
    def read_bytes(self, path: Path) -> bytes:
        """Read file contents for *path*."""
        ...

    def list_paths(self) -> tuple[Path, ...]:
        """Return all available file paths."""
        ...


@dataclass(frozen=True)
class DirectoryFileReader:
    root_dir: Path

    def read_bytes(self, path: Path) -> bytes:
        if path.is_absolute():
            raise ValueError(
                f"DirectoryFileReader paths must be relative, got absolute path: {path}"
            )

        file_path = resolve_path_within_base_dir(self.root_dir, path)
        return file_path.read_bytes()

    def list_paths(self) -> tuple[Path, ...]:
        return tuple(
            sorted(
                path.relative_to(self.root_dir)
                for path in self.root_dir.glob("**/*")
                if path.is_file()
            )
        )


@dataclass(frozen=True)
class InMemoryFileReader:
    """In-memory FileReader currently used only for testing purposes."""

    files: Mapping[Path, bytes]

    def read_bytes(self, path: Path) -> bytes:
        if path.is_absolute():
            raise ValueError(
                f"InMemoryFileReader paths must be relative, got absolute path: {path}"
            )

        if ".." in path.parts:
            raise ValueError(DIRECT_PATH_ERROR_MESSAGE)

        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]

    def list_paths(self) -> tuple[Path, ...]:
        return tuple(sorted(self.files))


def ensure_path_exists(path: Path) -> Path:
    """
    Ensure that the parent directory of the path exists.
    Returns the path itself to allow chaining.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resolve_path_within_base_dir(
    base_dir: Path,
    output_path: Path,
) -> Path:
    """Resolve *output_path* and ensure it stays within *base_dir*."""
    resolved_base_dir = base_dir.resolve()
    resolved_path = (base_dir / output_path).resolve()
    if not resolved_path.is_relative_to(resolved_base_dir):
        raise ValueError(DIRECT_PATH_ERROR_MESSAGE)
    return resolved_path


def read_directory(directory: Path) -> dict[Path, bytes]:
    """
    Read all files in a directory and return them as a dictionary.

    Args:
        directory: Path to the directory to read.

    Returns:
        Dictionary with keys as relative paths to the directory and values as the
        contents of the files.
    """
    file_reader = DirectoryFileReader(directory)
    return {path: file_reader.read_bytes(path) for path in file_reader.list_paths()}


def write_directory(files: Mapping[Path, bytes | str], directory: Path) -> None:
    """
    Write files to a directory.

    Args:
        files: Dictionary with keys as relative paths to the directory and values as
            the contents of the files.
        directory: Path to the directory to write the files to.
    """

    for relative_path, content in files.items():
        if relative_path.is_absolute():
            raise ValueError(
                f"write_directory files must use relative paths, got absolute path: {relative_path}"
            )
        file_path = resolve_path_within_base_dir(directory, relative_path)

        if isinstance(content, bytes):
            ensure_path_exists(file_path).write_bytes(content)
        elif isinstance(content, str):
            ensure_path_exists(file_path).write_text(content)
        else:
            raise TypeError(
                f"Content for {file_path} must be bytes or str, not {type(content)}."
            )
