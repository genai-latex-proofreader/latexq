from pathlib import Path

from tests.utils import run_lq_cli
from lq.utils.io import write_directory


def _run_flatten(input_file: Path, output_file: Path, query: str | None = None) -> None:
    args = [
        "flatten",
        "--input-file",
        str(input_file),
        "--output-file",
        str(output_file),
    ]
    if query is not None:
        args.extend(["--query", query])
    run_lq_cli(*args)


FLATTEN_DOCS_EXAMPLE_MAIN = r"""\documentclass{article}
\begin{document}
\maketitle
\input{intro}
\input{methods}
\end{document}"""

FLATTEN_DOCS_EXAMPLE_INTRO = r"""\section{Introduction}
\label{sec:intro}
This is the introduction.
"""

FLATTEN_DOCS_EXAMPLE_METHODS = r"""\section{Methods}
\label{sec:methods}
This is the methods section.
"""


def _write_flatten_example_project(input_dir: Path) -> None:
    write_directory(
        {
            Path("main.tex"): FLATTEN_DOCS_EXAMPLE_MAIN,
            Path("intro.tex"): FLATTEN_DOCS_EXAMPLE_INTRO,
            Path("methods.tex"): FLATTEN_DOCS_EXAMPLE_METHODS,
        },
        input_dir,
    )


def test_flatten_without_query_matches_lq_flatten_docs_example(tmp_path: Path):
    input_dir = tmp_path / "paper"
    _write_flatten_example_project(input_dir)

    output_file = tmp_path / "out" / "full.tex"
    rerun_output_file = tmp_path / "out" / "full-rerun.tex"

    _run_flatten(input_dir / "main.tex", output_file)
    _run_flatten(output_file, rerun_output_file)

    assert (
        output_file.read_text()
        == r"""\documentclass{article}
\begin{document}
\maketitle
\section{Introduction}
\label{sec:intro}
This is the introduction.
\section{Methods}
\label{sec:methods}
This is the methods section.
\end{document}"""
    )
    assert rerun_output_file.read_text() == output_file.read_text()


def test_flatten_query_with_methods_p0_matches_lq_flatten_docs_example(
    tmp_path: Path,
):
    input_dir = tmp_path / "paper"
    _write_flatten_example_project(input_dir)

    output_file = tmp_path / "out" / "intro-methods-outline.tex"

    _run_flatten(
        input_dir / "main.tex",
        output_file,
        query="@sec:intro @sec:methods[p0]",
    )

    assert (
        output_file.read_text()
        == r"""\documentclass{article}
\begin{document}
\maketitle
\section{Introduction}
\label{sec:intro}
This is the introduction.
\section{Methods}
\label{sec:methods}

(lq: the rest of this section has been truncated)
\end{document}
"""
    )


def test_flatten_query_can_remove_required_macro_definition(tmp_path: Path):
    input_file = tmp_path / "paper.tex"
    write_directory(
        {
            Path("paper.tex"): r"""\documentclass{article}
\begin{document}
\maketitle
\section{Macro Definitions}
\label{sec:defs}
\newcommand{\vect}[1]{\mathbf{#1}}

\section{Introduction}
\label{sec:intro}
We use \vect{x} in this section.
\end{document}"""
        },
        tmp_path,
    )

    output_file = tmp_path / "intro-only.tex"
    _run_flatten(input_file, output_file, query="@sec:intro")

    flattened = output_file.read_text()
    assert r"\newcommand{\vect}" not in flattened
    assert r"\vect{x}" in flattened
