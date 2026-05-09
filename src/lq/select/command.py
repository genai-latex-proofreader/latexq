from pathlib import Path

from lq.latex_interface.parser import parse_latex_from_files
from lq.query import (
    build_document_index,
    evaluate_query,
    parse_query,
    render_query_output,
    resolve_render_decisions,
)
from lq.select.data_model import SelectionQueryRequest
from lq.utils.io import DirectoryFileReader
from lq.utils.output import OutputWriter


def render_selected_output(
    input_file: Path,
    query_request: SelectionQueryRequest,
) -> str:
    input_path = input_file.resolve()
    file_reader = DirectoryFileReader(input_path.parent)
    document = parse_latex_from_files(
        file_reader,
        Path(input_path.name),
        supporting_file_paths=[],
    )
    document_index = build_document_index(document)
    evaluated_query = evaluate_query(
        document_index,
        parse_query(query_request.query_text),
    )
    return render_query_output(
        document,
        resolve_render_decisions(document_index, evaluated_query),
        output_mode=query_request.output_mode,
    )


def select_command(
    input_file: Path,
    output_writer: OutputWriter,
    query_request: SelectionQueryRequest,
) -> None:
    output_writer(render_selected_output(input_file, query_request))
