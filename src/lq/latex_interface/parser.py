from pathlib import Path

from lq.latex_interface.data_model import LatexDocument
from lq.latex_interface.s5_structure_parser import (
    parse_from_latex_with_structure_parser,
    parse_latex_from_files_with_structure_parser,
)
from lq.utils.io import FileReader


def parse_from_latex(
    input_latex: str,
    supporting_files: dict[Path, bytes] | None = None,
) -> LatexDocument:
    """Parse LaTeX through the active structural parser."""
    return parse_from_latex_with_structure_parser(
        input_latex,
        supporting_files=supporting_files,
    )


def parse_latex_from_files(
    file_reader: FileReader,
    main_file: Path,
    supporting_file_paths: list[Path],
    supporting_files: dict[Path, bytes] | None = None,
) -> LatexDocument:
    r"""Resolve ``\input{}`` directives and parse through the active parser."""
    return parse_latex_from_files_with_structure_parser(
        file_reader,
        main_file,
        supporting_file_paths,
        supporting_files=supporting_files,
    )
