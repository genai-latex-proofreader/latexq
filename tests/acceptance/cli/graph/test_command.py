import json
from pathlib import Path

from tests.utils import run_lq_cli


def test_cli_graph_text_output(tmp_path: Path, capsys):
    test_tex = tmp_path / "test.tex"
    test_tex.write_text(
        r"""\documentclass[11pt]{article}
\usepackage{amsmath}
\usepackage{cleveref}
\usepackage{varioref}
\author{Test Author}
\date{}
\begin{document}

\maketitle

\section{Intro}
\label{sec:intro}
In Section \ref{sec:background} we will prove equation \eqref{eq:einstein}.
See \cref{sub:proof}.
See \vref{sec:background}.
See \cref{sec:background,sub:proof}.

\section{Background}
\label{sec:background}
\label{eq:einstein}
Background text.

\subsection{Proof}
\label{sub:proof}
See \pageref{sec:intro}.
\end{document}"""
    )

    run_lq_cli(
        "graph",
        "--input-file",
        str(test_tex),
        "--stdout",
        "--format",
        "text",
    )

    captured = capsys.readouterr()
    assert (
        captured.out
        == """Nodes:
Main body:
- Intro (sec:intro in test.tex)
- Background (sec:background in test.tex)
  - Proof (sub:proof in test.tex)
Appendix:
  (none)

Edges:
sec:intro -> sec:background (x4)
sec:intro -> sub:proof (x2)
sub:proof -> sec:intro (x1)"""
    )
    assert captured.err == ""


def test_cli_graph_json_output_includes_warnings_in_encounter_order(
    tmp_path: Path, capsys
):
    test_tex = tmp_path / "test.tex"
    test_tex.write_text(
        r"""\documentclass[11pt]{article}
\usepackage{amsmath}
\usepackage{cleveref}
\usepackage{varioref}
\author{Test Author}
\date{}
\begin{document}

\maketitle

Preface text.
\label{main:preface}

\section{Intro}
\label{sec:intro}
See \ref{main:preface}.
See \ref{eq:detail}.
See \ref{missing:label}.

\section{Methods}
See \ref{sec:intro}.

\section{Target}
\label{sec:target}
\subsection{Detail}
\emph{Lead-in}
\label{eq:detail}
Detail text.
\end{document}"""
    )

    run_lq_cli(
        "graph",
        "--input-file",
        str(test_tex),
        "--stdout",
        "--format",
        "json",
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload == {
        "nodes": [
            {
                "kind": "section",
                "label": "sec:intro",
                "parent": None,
                "document_order": 0,
                "sibling_order": 0,
                "title": "Intro",
                "in_appendix": False,
                "source_file": "test.tex",
            },
            {
                "kind": "section",
                "label": "sec:target",
                "parent": None,
                "document_order": 1,
                "sibling_order": 1,
                "title": "Target",
                "in_appendix": False,
                "source_file": "test.tex",
            },
        ],
        "edges": [],
        "warnings": [
            {
                "code": "reference_label_without_selectable_node",
                "message": "Skipped reference 'main:preface' from sec:intro because the label exists but is outside selectable structural nodes.",
                "source_node_id": "sec:intro",
                "source_node_title": "Intro",
                "source_node_kind": "section",
                "referenced_label": "main:preface",
                "target_node_label": None,
                "target_node_title": None,
                "target_node_kind": None,
            },
            {
                "code": "unlabeled_target_node",
                "message": "Skipped reference 'eq:detail' from sec:intro because its containing subsection node 'Detail' is unlabeled.",
                "source_node_id": "sec:intro",
                "source_node_title": "Intro",
                "source_node_kind": "section",
                "referenced_label": "eq:detail",
                "target_node_label": None,
                "target_node_title": "Detail",
                "target_node_kind": "subsection",
            },
            {
                "code": "missing_reference_label",
                "message": "Skipped reference 'missing:label' from sec:intro because the label does not exist in the parsed document.",
                "source_node_id": "sec:intro",
                "source_node_title": "Intro",
                "source_node_kind": "section",
                "referenced_label": "missing:label",
                "target_node_label": None,
                "target_node_title": None,
                "target_node_kind": None,
            },
            {
                "code": "unlabeled_source_node",
                "message": "Skipped outgoing references from unlabeled section 'Methods'.",
                "source_node_id": None,
                "source_node_title": "Methods",
                "source_node_kind": "section",
                "referenced_label": None,
                "target_node_label": None,
                "target_node_title": None,
                "target_node_kind": None,
            },
        ],
    }
    assert captured.err.splitlines() == [
        "lq graph: warning: Skipped reference 'main:preface' from sec:intro because the label exists but is outside selectable structural nodes.",
        "lq graph: warning: Skipped reference 'eq:detail' from sec:intro because its containing subsection node 'Detail' is unlabeled.",
        "lq graph: warning: Skipped reference 'missing:label' from sec:intro because the label does not exist in the parsed document.",
        "lq graph: warning: Skipped outgoing references from unlabeled section 'Methods'.",
    ]


def test_cli_graph_writes_to_output_file(tmp_path: Path, capsys):
    test_tex = tmp_path / "test.tex"
    test_tex.write_text(
        r"""\documentclass[11pt]{article}
\usepackage{amsmath}
\usepackage{cleveref}
\usepackage{varioref}
\author{Test Author}
\date{}
\begin{document}

\maketitle

\section{Intro}
\label{sec:intro}
See \ref{sec:background}.

\section{Background}
\label{sec:background}
Background text.
\end{document}"""
    )
    output_file = tmp_path / "graph.txt"

    run_lq_cli(
        "graph",
        "--input-file",
        str(test_tex),
        "--output-file",
        str(output_file),
        "--format",
        "text",
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert (
        output_file.read_text()
        == """Nodes:
Main body:
- Intro (sec:intro in test.tex)
- Background (sec:background in test.tex)
Appendix:
  (none)

Edges:
sec:intro -> sec:background (x1)"""
    )
