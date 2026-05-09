from pathlib import Path

import pytest

from tests.utils import run_lq_cli
from lq.flatten.command import flatten_command
from lq.query import SECTION_TRUNCATION_NOTICE
from lq.utils.io import read_directory, write_directory

SECTION_NOTICE = SECTION_TRUNCATION_NOTICE.rstrip("\n")

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


def test_cli_with_test_tex(tmp_path: Path):
    test_tex = tmp_path / "test.tex"
    input_content = r"""\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\author{Test Author}
\date{}
\begin{document}

\maketitle

\section{Intro}
\label{sec:intro}
Hello World!
\end{document}"""
    test_tex.write_text(input_content)
    out_tex = tmp_path / "out.tex"

    run_lq_cli(
        "flatten",
        "--input-file",
        str(test_tex),
        "--output-file",
        str(out_tex),
    )

    assert out_tex.exists()
    assert out_tex.read_text() == input_content


def test_flatten_writes_only_requested_output_file(tmp_path: Path):
    input_content = r"""\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\author{Test Author}
\date{}
\begin{document}

\maketitle

\section{Intro}
\label{sec:intro}
Hello World!
\end{document}"""
    test_tex = tmp_path / "test.tex"
    write_directory(
        {
            Path("test.tex"): input_content,
            Path("notes.txt"): "supporting content",
        },
        tmp_path,
    )

    output_dir = tmp_path / "out"
    out_tex = output_dir / "flat.tex"

    run_lq_cli(
        "flatten",
        "--input-file",
        str(test_tex),
        "--output-file",
        str(out_tex),
    )

    assert read_directory(output_dir) == {Path("flat.tex"): input_content.encode()}


def test_flatten_requires_output_file(tmp_path: Path, capsys):
    test_tex = tmp_path / "test.tex"
    test_tex.write_text(QUERYABLE_INPUT)

    with pytest.raises(SystemExit) as excinfo:
        run_lq_cli(
            "flatten",
            "--input-file",
            str(test_tex),
        )

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "the following arguments are required: --output-file" in captured.err


def test_flatten_command_without_query_preserves_existing_output(tmp_path: Path):
    test_tex = tmp_path / "test.tex"
    test_tex.write_text(QUERYABLE_INPUT)

    written: list[str] = []

    flatten_command(test_tex, written.append, None)  # check also non-standard writer

    assert written == [QUERYABLE_INPUT]


def test_cli_flatten_query_outputs_latex_document(tmp_path: Path, capsys):
    test_tex = tmp_path / "test.tex"
    test_tex.write_text(QUERYABLE_INPUT)
    output_file = tmp_path / "selected.tex"

    run_lq_cli(
        "flatten",
        "--input-file",
        str(test_tex),
        "--output-file",
        str(output_file),
        "--query",
        "@sec:intro[p1]",
    )

    captured = capsys.readouterr()

    expected_output = r"""\documentclass[11pt]{article}
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

<SECTION_NOTICE>
\end{document}
""".replace("<SECTION_NOTICE>", SECTION_NOTICE)

    assert output_file.read_text() == expected_output
    assert captured.out == ""
    assert captured.err == ""


def test_cli_flatten_surfaces_query_syntax_error(tmp_path: Path, capsys):
    test_tex = tmp_path / "test.tex"
    test_tex.write_text(QUERYABLE_INPUT)
    output_file = tmp_path / "selected.tex"

    with pytest.raises(SystemExit) as excinfo:
        run_lq_cli(
            "flatten",
            "--input-file",
            str(test_tex),
            "--output-file",
            str(output_file),
            "--query",
            "@",
        )

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid query syntax" in captured.err
    assert "Expected label or '..' after '@'." in captured.err
