from pathlib import Path

from lq.latex_interface.data_model import to_latex
from lq.latex_interface.parser import parse_latex_from_files
from lq.query import LatexQueryText
from lq.select import SelectionQueryRequest, render_selected_output
from lq.utils.io import DirectoryFileReader
from lq.utils.output import OutputWriter


def render_flattened_latex(
    input_file: Path,
    query_text: LatexQueryText | None,
) -> str:
    input_path = input_file.resolve()
    file_reader = DirectoryFileReader(input_path.parent)
    doc = parse_latex_from_files(
        file_reader,
        Path(input_path.name),
        supporting_file_paths=[],
    )

    if query_text is None:
        return to_latex(doc)

    return render_selected_output(
        input_file,
        SelectionQueryRequest(
            query_text=query_text,
            output_mode="latex",
        ),
    )


def flatten_command(
    input_file: Path,
    output_writer: OutputWriter,
    query_text: LatexQueryText | None,
) -> None:
    flattened_latex = render_flattened_latex(
        input_file,
        query_text,
    )
    output_writer(flattened_latex)
