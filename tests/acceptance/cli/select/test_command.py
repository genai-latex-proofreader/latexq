from pathlib import Path

import pytest

from tests.utils import run_lq_cli
from lq.query import SECTION_TRUNCATION_NOTICE
from lq.select import SelectionQueryRequest, select_command

QUERYABLE_INPUT = r"""\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\author{Test Author}
\date{}
\begin{document}

\maketitle

Main preface
\label{main:preface}

\section{Intro}
\label{sec:intro}
Intro one.

Intro two.

\appendix

Appendix preface
\label{app:preface}

\section{Proofs}
\label{sec:app:proofs}
Proof text.
\end{document}"""


def test_cli_select_defaults_to_stdout(tmp_path: Path, capsys):
    test_tex = tmp_path / "test.tex"
    test_tex.write_text(QUERYABLE_INPUT)

    run_lq_cli(
        "select",
        "--input-file",
        str(test_tex),
        "--query",
        "@sec:intro[p1]",
    )

    captured = capsys.readouterr()

    assert (
        captured.out
        == rf"""\section{{Intro}}
\label{{sec:intro}}
Intro one.

{SECTION_TRUNCATION_NOTICE.rstrip("\n")}
"""
    )
    assert captured.err == ""


def test_cli_select_writes_to_output_file(tmp_path: Path, capsys):
    test_tex = tmp_path / "test.tex"
    test_tex.write_text(QUERYABLE_INPUT)
    output_file = tmp_path / "selected.tex"

    run_lq_cli(
        "select",
        "--input-file",
        str(test_tex),
        "--output-file",
        str(output_file),
        "--query",
        "app",
    )

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == ""
    assert (
        output_file.read_text()
        == r"""\section{Proofs}
\label{sec:app:proofs}
Proof text.
"""
    )


def test_select_command_emits_selected_nodes_only(tmp_path: Path):
    test_tex = tmp_path / "test.tex"
    test_tex.write_text(QUERYABLE_INPUT)

    written: list[str] = []

    select_command(
        test_tex,
        written.append,
        SelectionQueryRequest(query_text="app", output_mode="fragment"),
    )

    assert written == [
        r"""\section{Proofs}
\label{sec:app:proofs}
Proof text.
"""
    ]


def test_cli_select_surfaces_query_syntax_error(tmp_path: Path, capsys):
    test_tex = tmp_path / "test.tex"
    test_tex.write_text(QUERYABLE_INPUT)

    with pytest.raises(SystemExit) as excinfo:
        run_lq_cli(
            "select",
            "--input-file",
            str(test_tex),
            "--query",
            "@",
        )

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid query syntax" in captured.err
    assert "Expected label or '..' after '@'." in captured.err
