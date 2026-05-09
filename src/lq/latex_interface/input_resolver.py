import re
from pathlib import Path
from typing import Iterator, Set

from lq.latex_interface.data_model import LatexLabel, ResolvedLatexIncludes
from lq.utils.io import FileReader

UNESCAPED_PERCENT_PATTERN = re.compile(r"(?<!\\)%")
LABEL_COMMAND_PATTERN = re.compile(r"\\label\s*\{([^{}]+)\}")


def resolve_input_path(input_command_fileref: str, current_file: Path) -> Path:
    r"""
    Resolve an input file reference relative to current file location.

    Handles:
    - \input{filename} -> filename.tex
    - \input{filename.tex} -> filename.tex
    - Relative paths from current file's directory
    """
    filename = input_command_fileref.strip()

    # Add .tex extension if not present
    if not filename.endswith(".tex"):
        filename += ".tex"

    return current_file.parent / filename


def _code_part(line: str) -> str:
    """Return the non-comment portion of *line* (text before the first ``%``)."""
    percent_match = UNESCAPED_PERCENT_PATTERN.search(line)
    if percent_match is None:
        return line
    return line[: percent_match.start()]


def _collect_line_labels(code: str) -> tuple[LatexLabel, ...]:
    return tuple(
        label
        for match in LABEL_COMMAND_PATTERN.finditer(code)
        if (label := match.group(1).strip()) != ""
    )


def _iter_expanded_lines(
    file_reader: FileReader,
    main_file: Path,
    supporting_file_paths: list[Path],
) -> Iterator[tuple[str, Path]]:
    supporting_file_path_set = set(supporting_file_paths)

    def _expand_file(
        file_path: Path,
        processing_stack: Set[Path],
    ) -> Iterator[tuple[str, Path]]:
        # Check for circular dependency
        if file_path in processing_stack:
            cycle_path = (
                " -> ".join(str(p) for p in processing_stack) + f" -> {file_path}"
            )
            raise ValueError(
                f"Circular input dependency detected:\n  {cycle_path}\n"
                f"This creates an infinite inclusion loop."
            )

        try:
            file_contents = file_reader.read_bytes(file_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Input file '{file_path}' not found.") from exc

        # Create new stack with current file added
        new_stack = processing_stack | {file_path}

        for line in file_contents.decode("utf-8").splitlines(keepends=True):
            code = _code_part(line)
            stripped_line = line.lstrip(" \t")
            # lq recognizes \input{...} only when it occupies its own logical
            # line, allowing optional leading indentation.
            input_match = re.match(
                r"^\\input\{([^}]+)\}\s*(?:\r?\n)?$",
                stripped_line,
            )

            if input_match:
                input_filename = input_match.group(1)
                input_path = resolve_input_path(input_filename, file_path)

                if input_path in supporting_file_path_set:
                    yield line, file_path
                else:
                    yield from _expand_file(input_path, new_stack)
            else:
                # Keep the requirement strict so split/flatten round-trips stay
                # predictable and simple to validate.
                if r"\input{" in code:
                    raise ValueError(
                        r"lq requires \input{...} to be the only non-whitespace "
                        r"content on its line, aside from optional leading indentation. "
                        f"Found: {line!r}"
                    )
                yield line, file_path

    return _expand_file(main_file, set())


def resolve_latex_includes(
    file_reader: FileReader,
    main_file: Path,
    supporting_file_paths: list[Path],
) -> ResolvedLatexIncludes:
    r"""Resolve ``\input{}`` commands and collect label source provenance.

    Recursively expands ``\input{}`` directives while preserving the rest
    of the content — including LaTeX comments — verbatim.

    Label source tracking in this resolver is line-based: after stripping the
    comment portion of each expanded line, occurrences of ``\label{...}`` are
    detected and recorded here without parsing unrelated commands on the line.

    Args:
        file_reader: File reader used to load files on demand.
        main_file: Path to the main LaTeX file.
        supporting_file_paths: List of file paths to leave unexpanded when
            referenced by ``\input{...}``.

    Returns:
        A :class:`ResolvedLatexIncludes` with expanded content and label
        source mapping.

    Raises:
        FileNotFoundError: If any input file (including main file) is missing.
        ValueError: If circular dependencies are detected, or ``\input{}``
            appears on a line with other non-whitespace content besides
            optional leading indentation.

    See Also:
        :class:`ResolvedLatexIncludes` for field-level semantics.
    """
    expanded_lines: list[str] = []
    label_source_files: dict[LatexLabel, Path] = {}

    for line, file_path in _iter_expanded_lines(
        file_reader,
        main_file,
        supporting_file_paths,
    ):
        expanded_lines.append(line)

        code = _code_part(line)
        for label in _collect_line_labels(code):
            label_source_files.setdefault(label, file_path)

    return ResolvedLatexIncludes(
        expanded_latex="".join(expanded_lines),
        label_source_files=label_source_files,
    )
