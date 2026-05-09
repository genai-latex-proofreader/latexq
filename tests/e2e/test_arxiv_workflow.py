import gzip
import json
import re
import tarfile
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from lq.config import LatexqConfig, save_config
from lq.flatten.command import render_flattened_latex
from lq.latex_interface.data_model import to_latex
from lq.latex_interface.parser import parse_from_latex
from lq.split.data_model import Granularity, SplitConfig
from tests.utils import run_lq_cli

type InputFileTransform = Callable[[Path], None]
type InputFileTransformPlan = dict[str, tuple[InputFileTransform, ...]]


def _strip_preamble_before_documentclass(input_file: Path) -> None:
    input_bytes = input_file.read_bytes()
    documentclass_offset = input_bytes.find(rb"\documentclass")
    assert documentclass_offset >= 0, rf"Expected \documentclass in {input_file}"
    input_file.write_bytes(input_bytes[documentclass_offset:])


def _left_align_line_started_commands(input_file: Path) -> None:
    input_bytes = input_file.read_bytes()
    normalized_bytes = re.sub(
        rb"(?m)^[ \t]+(\\(?:appendix|section|subsection|input)\b)",
        rb"\1",
        input_bytes,
    )
    input_file.write_bytes(normalized_bytes)


@dataclass(frozen=True)
class ArxivWorkflowCase:
    arxiv_id: str
    main_tex_path: Path
    input_file_transformations: InputFileTransformPlan
    query_label: str
    required_graph_labels: tuple[str, ...]
    select_output_fragments: tuple[str, ...]
    expected_graph_node_count: int
    expected_graph_edge_count: int
    expected_section_split_files: tuple[Path, ...]
    expected_subsection_split_files: tuple[Path, ...]


ARXIV_WORKFLOW_CASES = (
    ArxivWorkflowCase(
        arxiv_id="1203.6336",
        main_tex_path=Path("arxiv-1203.6336.tex"),
        input_file_transformations={
            "arxiv-1203.6336.tex": (_strip_preamble_before_documentclass,),
        },
        query_label="sec:prelim",
        required_graph_labels=("sec:prelim", "sec:DoubleCones"),
        select_output_fragments=(
            r"\section{Preliminaries}",
            r"\label{sec:prelim}",
            r"By a \emph{manifold} $N$",
        ),
        expected_graph_node_count=13,
        expected_graph_edge_count=38,
        expected_section_split_files=(
            Path("arxiv-1203.6336.tex"),
            Path("sections/s01.tex"),
            Path("sections/s02_sec_prelim.tex"),
            Path("sections/s03_sec_normalformsww.tex"),
            Path("sections/s04_eq_twochar.tex"),
            Path("sections/s05_sec_doublecones.tex"),
        ),
        expected_subsection_split_files=(
            Path("arxiv-1203.6336.tex"),
            Path("sections/s01_00.tex"),
            Path("sections/s02_00_sec_prelim.tex"),
            Path("sections/s02_01.tex"),
            Path("sections/s02_02.tex"),
            Path("sections/s02_03_sec_maxon4.tex"),
            Path("sections/s02_04_media_decomp.tex"),
            Path("sections/s02_05_sec_fresnelsurface.tex"),
            Path("sections/s03_00_sec_normalformsww.tex"),
            Path("sections/s03_01_sec_normalschuller.tex"),
            Path("sections/s03_02_sec_nonbire.tex"),
            Path("sections/s03_03_sec_mediumwithdoublelightcone.tex"),
            Path("sections/s04_00_eq_twochar.tex"),
            Path("sections/s04_01_sec_planewavesinr4.tex"),
            Path("sections/s04_02_sec_decompo.tex"),
            Path("sections/s04_03_sec_44factorisability.tex"),
            Path("sections/s05_00_sec_doublecones.tex"),
        ),
    ),
    ArxivWorkflowCase(
        arxiv_id="1108.4198",
        main_tex_path=Path("arxiv-1108.4198.tex"),
        input_file_transformations={
            "*.tex": (_left_align_line_started_commands,),
            "arxiv-1108.4198.tex": (
                _strip_preamble_before_documentclass,
                _left_align_line_started_commands,
            ),
        },
        query_label="mainSec",
        required_graph_labels=("mainSec", "sec:MaxOn4", "sec:classification22"),
        select_output_fragments=(
            r"\section{Maxwell's equations}",
            r"\label{mainSec}",
            r"By a \emph{manifold} $M$",
        ),
        expected_graph_node_count=7,
        expected_graph_edge_count=14,
        expected_section_split_files=(
            Path("arxiv-1108.4198.tex"),
            Path("sections/s01.tex"),
            Path("sections/s02_mainsec.tex"),
            Path("sections/s03_sec_classification22.tex"),
            Path("appendix/a01_app_22tensor.tex"),
            Path("appendix/a02.tex"),
        ),
        expected_subsection_split_files=(
            Path("arxiv-1108.4198.tex"),
            Path("sections/s01_00.tex"),
            Path("sections/s02_00_mainsec.tex"),
            Path("sections/s02_01_sec_maxon4.tex"),
            Path("sections/s02_02_media_decomp.tex"),
            Path("sections/s02_03_sec_rep6x6.tex"),
            Path("sections/s02_04_sec_hodge.tex"),
            Path("sections/s02_05.tex"),
            Path("sections/s03_00_sec_classification22.tex"),
            Path("appendix/a01_00_app_22tensor.tex"),
            Path("appendix/a02_00.tex"),
        ),
    ),
    ArxivWorkflowCase(
        arxiv_id="1108.4207",
        main_tex_path=Path("arxiv-1-frame.tex"),
        input_file_transformations={
            "arxiv-1-frame.tex": (
                _strip_preamble_before_documentclass,
                _left_align_line_started_commands,
            ),
        },
        query_label="mainSec",
        required_graph_labels=("mainSec", "sec:MaxOn4", "sec:Rep6x6"),
        select_output_fragments=(
            r"\section{Maxwell's equations}",
            r"\label{mainSec}",
            r"By a \emph{manifold} $M$",
        ),
        expected_graph_node_count=3,
        expected_graph_edge_count=2,
        expected_section_split_files=(
            Path("arxiv-1-frame.tex"),
            Path("sections/s01_mainsec.tex"),
            Path("sections/s02.tex"),
        ),
        expected_subsection_split_files=(
            Path("arxiv-1-frame.tex"),
            Path("sections/s01_00_mainsec.tex"),
            Path("sections/s01_01_sec_maxon4.tex"),
            Path("sections/s01_02_sec_rep6x6.tex"),
            Path("sections/s01_03.tex"),
            Path("sections/s02_00.tex"),
            Path("sections/s02_01.tex"),
        ),
    ),
    ArxivWorkflowCase(
        arxiv_id="1103.3118",
        main_tex_path=Path("frame.tex"),
        input_file_transformations={
            "*.tex": (_left_align_line_started_commands,),
            "frame.tex": (
                _strip_preamble_before_documentclass,
                _left_align_line_started_commands,
            ),
        },
        query_label="mainSec",
        required_graph_labels=("mainSec", "sec:GOS", "sec:uni"),
        select_output_fragments=(
            r"\section{Maxwell's equations}",
            r"\label{mainSec}",
            r"By a \emph{manifold} $M$",
        ),
        expected_graph_node_count=13,
        expected_graph_edge_count=34,
        expected_section_split_files=(
            Path("frame.tex"),
            Path("sections/s01_sec_intro.tex"),
            Path("sections/s02_mainsec.tex"),
            Path("sections/s03_sec_gos.tex"),
            Path("sections/s04_sec_closure.tex"),
            Path("sections/s05_sec_uni.tex"),
            Path("appendix/a01_app_groebner.tex"),
            Path("appendix/a02_app_verylarge.tex"),
        ),
        expected_subsection_split_files=(
            Path("frame.tex"),
            Path("sections/s01_00_sec_intro.tex"),
            Path("sections/s02_00_mainsec.tex"),
            Path("sections/s02_01_sec_maxon4.tex"),
            Path("sections/s02_02_media_decomp.tex"),
            Path("sections/s02_03_sec_hodge.tex"),
            Path("sections/s02_04_sec_abcdtransrules.tex"),
            Path("sections/s03_00_sec_gos.tex"),
            Path("sections/s03_01.tex"),
            Path("sections/s03_02.tex"),
            Path("sections/s04_00_sec_closure.tex"),
            Path("sections/s05_00_sec_uni.tex"),
            Path("sections/s05_01_sec_trinjective1.tex"),
            Path("sections/s05_02_sec_trinjective2.tex"),
            Path("appendix/a01_00_app_groebner.tex"),
            Path("appendix/a02_00_app_verylarge.tex"),
        ),
    ),
)


def _apply_input_file_transformations(
    output_dir: Path, transform_plan: InputFileTransformPlan
) -> None:
    workspace_files = sorted(
        path.relative_to(output_dir) for path in output_dir.rglob("*") if path.is_file()
    )
    for pattern, transforms in transform_plan.items():
        for relative_path in workspace_files:
            if not relative_path.match(pattern):
                continue
            target_file = output_dir / relative_path
            for transform in transforms:
                transform(target_file)


def _download_arxiv_source(case: ArxivWorkflowCase, output_dir: Path) -> Path:
    source_url = f"https://arxiv.org/e-print/{case.arxiv_id}"

    try:
        with urlopen(source_url, timeout=60) as response:
            compressed_source = response.read()
    except URLError as error:
        pytest.fail(f"Failed to download arXiv source from {source_url}: {error}")

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(fileobj=BytesIO(compressed_source), mode="r:gz") as archive:
            archive.extractall(output_dir, filter="data")
    except tarfile.TarError:
        input_file = output_dir / case.main_tex_path
        input_file.write_bytes(gzip.decompress(compressed_source))
        _apply_input_file_transformations(output_dir, case.input_file_transformations)
        return input_file

    input_file = output_dir / case.main_tex_path
    assert input_file.exists(), f"Expected extracted arXiv source at {input_file}"
    _apply_input_file_transformations(output_dir, case.input_file_transformations)
    return input_file


def _write_split_config(config_file: Path, granularity: Granularity) -> None:
    save_config(
        LatexqConfig(
            split=SplitConfig(
                granularity=granularity,
                main_sections_dir="sections",
                appendix_sections_dir="appendix",
            )
        ),
        config_file,
    )


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _assert_graph_payload(
    graph_payload: dict[str, object], case: ArxivWorkflowCase
) -> None:
    nodes = graph_payload["nodes"]
    edges = graph_payload["edges"]

    assert isinstance(nodes, list)
    assert isinstance(edges, list)
    assert len(nodes) == case.expected_graph_node_count
    assert len(edges) == case.expected_graph_edge_count

    node_labels = {
        node["label"]
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("label"), str)
    }
    for label in case.required_graph_labels:
        assert label in node_labels


def _list_split_tex_files(output_dir: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(path.relative_to(output_dir) for path in output_dir.rglob("*.tex"))
    )


def _run_split_workflow(
    *,
    input_file: Path,
    config_file: Path,
    output_dir: Path,
    expected_files: tuple[Path, ...],
    capsys: pytest.CaptureFixture[str],
) -> Path:
    run_lq_cli(
        "split",
        "--input-file",
        str(input_file),
        "--output-dir",
        str(output_dir),
        "--config-file",
        str(config_file),
    )
    split_captured = capsys.readouterr()

    assert split_captured.out == ""
    assert set(_list_split_tex_files(output_dir)) == set(expected_files)

    split_main_file = output_dir / input_file.name
    assert split_main_file.exists()

    run_lq_cli(
        "split",
        "--input-file",
        str(split_main_file),
        "--config-file",
        str(config_file),
        "--validate",
    )
    validate_captured = capsys.readouterr()

    assert validate_captured.out == ""
    assert validate_captured.err == ""

    return split_main_file


def _run_arxiv_workflow_case(
    case: ArxivWorkflowCase,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_file = _download_arxiv_source(case, tmp_path / "paper")
    section_config_file = tmp_path / "lq-section.yaml"
    subsection_config_file = tmp_path / "lq-subsection.yaml"
    section_split_output_dir = tmp_path / "split-section"
    subsection_split_output_dir = tmp_path / "split-subsection"
    flattened_output_file = tmp_path / "flattened.tex"

    _write_split_config(section_config_file, Granularity.section)
    _write_split_config(subsection_config_file, Granularity.subsection)

    run_lq_cli(
        "graph",
        "--input-file",
        str(input_file),
        "--stdout",
        "--format",
        "json",
    )
    graph_captured = capsys.readouterr()
    graph_payload = json.loads(graph_captured.out)

    _assert_graph_payload(graph_payload, case)

    section_split_main_file = _run_split_workflow(
        input_file=input_file,
        config_file=section_config_file,
        output_dir=section_split_output_dir,
        expected_files=case.expected_section_split_files,
        capsys=capsys,
    )
    _run_split_workflow(
        input_file=input_file,
        config_file=subsection_config_file,
        output_dir=subsection_split_output_dir,
        expected_files=case.expected_subsection_split_files,
        capsys=capsys,
    )

    run_lq_cli(
        "flatten",
        "--input-file",
        str(section_split_main_file),
        "--output-file",
        str(flattened_output_file),
    )
    flatten_captured = capsys.readouterr()

    assert flatten_captured.out == ""
    assert flatten_captured.err == ""

    flattened_from_split = flattened_output_file.read_text()
    flattened_from_original = render_flattened_latex(input_file, None)

    assert _normalize_line_endings(flattened_from_split) == _normalize_line_endings(
        flattened_from_original
    )
    assert to_latex(parse_from_latex(flattened_from_split)) == flattened_from_split

    run_lq_cli(
        "select",
        "--input-file",
        str(input_file),
        "--stdout",
        "--query",
        f"@{case.query_label}",
    )
    select_captured = capsys.readouterr()

    for fragment in case.select_output_fragments:
        assert fragment in select_captured.out


@pytest.mark.e2e
@pytest.mark.parametrize(
    "case",
    ARXIV_WORKFLOW_CASES,
    ids=(
        "arxiv-1203.6336",
        "arxiv-1108.4198",
        "arxiv-1108.4207",
        "arxiv-1103.3118",
    ),
)
def test_arxiv_end_to_end_workflow(
    case: ArxivWorkflowCase, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _run_arxiv_workflow_case(case, tmp_path, capsys)
