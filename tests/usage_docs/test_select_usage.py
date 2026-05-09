from pathlib import Path

from tests.utils import run_lq_cli
from lq.utils.io import write_directory


def _run_select(input_file: Path, query: str, output_file: Path | None = None) -> None:
    args = [
        "select",
        "--input-file",
        str(input_file),
        "--query",
        query,
    ]
    if output_file is not None:
        args.extend(["--output-file", str(output_file)])
    run_lq_cli(*args)


SELECT_DOCS_EXAMPLE_MAIN = r"""\documentclass{article}
\begin{document}
\maketitle
\section{Introduction}
\label{sec:intro}
This is the intro.
\section{Methods}
\label{sec:methods}
This is the methods.
\end{document}"""


def _write_select_example_project(input_dir: Path) -> Path:
    main_file = input_dir / "main.tex"
    write_directory(
        {
            Path("main.tex"): SELECT_DOCS_EXAMPLE_MAIN,
        },
        input_dir,
    )
    return main_file


def test_select_stdout_matches_docs_example(tmp_path: Path, capsys) -> None:
    input_dir = tmp_path / "paper"
    main_file = _write_select_example_project(input_dir)

    _run_select(main_file, query="@sec:intro")

    captured = capsys.readouterr()
    assert (
        captured.out.strip()
        == r"""\section{Introduction}
\label{sec:intro}
This is the intro."""
    )


def test_select_file_matches_docs_example(tmp_path: Path) -> None:
    input_dir = tmp_path / "paper"
    main_file = _write_select_example_project(input_dir)

    output_file = tmp_path / "out" / "intro-fragment.tex"

    _run_select(main_file, query="@sec:intro", output_file=output_file)

    assert (
        output_file.read_text().strip()
        == r"""\section{Introduction}
\label{sec:intro}
This is the intro."""
    )
