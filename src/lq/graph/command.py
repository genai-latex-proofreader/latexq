import sys
from pathlib import Path
from typing import Literal

from lq.graph.builder import build_reference_graph
from lq.graph.data_model import GraphWarning
from lq.graph.render_json import render_json
from lq.graph.render_text import render_text
from lq.latex_interface.input_resolver import resolve_latex_includes
from lq.latex_interface.parser import parse_from_latex
from lq.utils.io import DirectoryFileReader
from lq.utils.output import OutputWriter

GraphOutputFormat = Literal["text", "json"]


def render_reference_graph(input_file: Path, output_format: GraphOutputFormat) -> str:
    input_path = input_file.resolve()
    file_reader = DirectoryFileReader(input_path.parent)
    resolved_inputs = resolve_latex_includes(
        file_reader,
        Path(input_path.name),
        supporting_file_paths=[],
    )
    document = parse_from_latex(resolved_inputs.expanded_latex)
    reference_graph = build_reference_graph(document)

    if output_format == "text":
        return render_text(reference_graph, resolved_inputs.label_source_files)

    return render_json(reference_graph, resolved_inputs.label_source_files)


def graph_command(
    input_file: Path,
    output_writer: OutputWriter,
    output_format: GraphOutputFormat,
) -> None:
    input_path = input_file.resolve()
    file_reader = DirectoryFileReader(input_path.parent)
    resolved_inputs = resolve_latex_includes(
        file_reader,
        Path(input_path.name),
        supporting_file_paths=[],
    )
    document = parse_from_latex(resolved_inputs.expanded_latex)
    reference_graph = build_reference_graph(document)

    if output_format == "text":
        output_writer(render_text(reference_graph, resolved_inputs.label_source_files))
    else:
        output_writer(render_json(reference_graph, resolved_inputs.label_source_files))

    for warning in reference_graph.warnings:
        sys.stderr.write(_render_warning_line(warning))


def _render_warning_line(warning: GraphWarning) -> str:
    return f"lq graph: warning: {warning.message}\n"
