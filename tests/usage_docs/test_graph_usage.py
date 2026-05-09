import json
from pathlib import Path

from tests.utils import run_lq_cli

GRAPH_DOCS_EXAMPLE_MANUSCRIPT = r"""\documentclass{article}
\title{Example}
\begin{document}
\maketitle

\section{Introduction}
\label{sec:intro}
In Section \ref{sec:background} we will prove equation \eqref{eq:einstein}.

\section{Background}
\label{sec:background}
Background text.

\begin{equation}
  E = mc^2
\label{eq:einstein}
\end{equation}

\subsection{Details}
\label{sub:details}
See \ref{sec:intro}.

\end{document}
"""


def _run_graph(
    input_file: Path,
    output_format: str,
) -> None:
    run_lq_cli(
        "graph",
        "--input-file",
        str(input_file),
        "--stdout",
        "--format",
        output_format,
    )


def test_graph_text_output_matches_lq_graph_docs_example(tmp_path: Path, capsys):
    input_file = tmp_path / "paper.tex"
    input_file.write_text(GRAPH_DOCS_EXAMPLE_MANUSCRIPT)

    _run_graph(input_file, "text")

    captured = capsys.readouterr()
    assert (
        captured.out
        == """Nodes:
Main body:
- Introduction (sec:intro in paper.tex)
- Background (sec:background in paper.tex)
  - Details (sub:details in paper.tex)
Appendix:
  (none)

Edges:
sec:intro -> sec:background (x2)
sub:details -> sec:intro (x1)"""
    )
    assert captured.err == ""


def test_graph_json_output_matches_lq_graph_docs_example(tmp_path: Path, capsys):
    input_file = tmp_path / "paper.tex"
    input_file.write_text(GRAPH_DOCS_EXAMPLE_MANUSCRIPT)

    _run_graph(input_file, "json")

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    # The docs omit ordering fields for brevity. Remove these:
    nodes_without_ordering = [
        {
            "kind": node["kind"],
            "label": node["label"],
            "parent": node["parent"],
            "title": node["title"],
            "in_appendix": node["in_appendix"],
            "source_file": node["source_file"],
        }
        for node in payload["nodes"]
    ]

    assert {
        "nodes": nodes_without_ordering,
        "edges": payload["edges"],
        "warnings": payload["warnings"],
    } == {
        "nodes": [
            {
                "kind": "section",
                "label": "sec:intro",
                "parent": None,
                "title": "Introduction",
                "in_appendix": False,
                "source_file": "paper.tex",
            },
            {
                "kind": "section",
                "label": "sec:background",
                "parent": None,
                "title": "Background",
                "in_appendix": False,
                "source_file": "paper.tex",
            },
            {
                "kind": "subsection",
                "label": "sub:details",
                "parent": "sec:background",
                "title": "Details",
                "in_appendix": False,
                "source_file": "paper.tex",
            },
        ],
        "edges": [
            {
                "source": "sec:intro",
                "target": "sec:background",
                "count": 2,
                "target_referenced_labels": ["sec:background", "eq:einstein"],
            },
            {
                "source": "sub:details",
                "target": "sec:intro",
                "count": 1,
                "target_referenced_labels": ["sec:intro"],
            },
        ],
        "warnings": [],
    }
    assert captured.err == ""
