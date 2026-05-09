from collections.abc import Callable
from pathlib import Path

import pytest

from lq.split.data_model import Granularity
from lq.utils.io import ensure_path_exists, write_directory

from .helpers import (
    LATEX_WITH_SUBSECTION,
    make_split_config,
    run_split,
    run_validate,
)


def _mutate_path_drift(output_dir: Path) -> None:
    (output_dir / "sections/s01_00_sec_intro.tex").rename(
        output_dir / "sections/s09_00_sec_intro.tex"
    )
    (output_dir / "test.tex").write_text(
        (output_dir / "test.tex")
        .read_text()
        .replace("sections/s01_00_sec_intro.tex", "sections/s09_00_sec_intro.tex")
    )


def _mutate_orphan_file(output_dir: Path) -> None:
    ensure_path_exists(output_dir / "sections/s99_00_sec_orphan.tex").write_text(
        r"""\section{Orphan}
"""
    )


def _mutate_main_file_content(output_dir: Path) -> None:
    (output_dir / "test.tex").write_text(
        (output_dir / "test.tex")
        .read_text()
        .replace(r"\end{document}", "% drift\n" + r"\end{document}")
    )


@pytest.mark.parametrize("leading_whitespace", ["", "  "])
@pytest.mark.parametrize("trailing_whitespace", ["", "  "])
def test_split_accepts_input_with_surrounding_whitespace(
    tmp_path: Path,
    capsys,
    leading_whitespace: str,
    trailing_whitespace: str,
):
    config = make_split_config(Granularity.section)
    input_file = tmp_path / "test.tex"
    output_dir = tmp_path / "out"
    input_latex = r"""\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\author{Test Author}
\date{}
\begin{document}

\maketitle
\appendix

__LEADING__\input{appendix/a01_sec_proof.tex}__TRAILING__
\end{document}""".replace("__LEADING__", leading_whitespace).replace(
        "__TRAILING__", trailing_whitespace
    )

    write_directory(
        {
            Path("test.tex"): input_latex,
            Path("appendix/a01_sec_proof.tex"): r"""\section{Proof}
\label{sec:proof}
Proof text.
""",
        },
        tmp_path,
    )

    run_split(input_file, output_dir, config)
    run_validate(output_dir / "test.tex", config)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_split_validate_passes_for_matching_split_output(tmp_path: Path, capsys):
    input_file = tmp_path / "test.tex"
    output_dir = tmp_path / "out"
    config = make_split_config(Granularity.subsection)

    write_directory({Path("test.tex"): LATEX_WITH_SUBSECTION}, tmp_path)
    run_split(input_file, output_dir, config)

    run_validate(output_dir / "test.tex", config)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.parametrize(
    ("mutate_output", "expected_error"),
    [
        pytest.param(
            _mutate_path_drift,
            "path drift: actual sections/s09_00_sec_intro.tex expected sections/s01_00_sec_intro.tex",
            id="path-drift",
        ),
        pytest.param(
            _mutate_orphan_file,
            "orphan file: sections/s99_00_sec_orphan.tex",
            id="orphan-file",
        ),
        pytest.param(
            _mutate_main_file_content,
            "content drift: test.tex",
            id="main-file-content-drift",
        ),
    ],
)
def test_split_validate_reports_drift(
    tmp_path: Path,
    capsys,
    mutate_output: Callable[[Path], None],
    expected_error: str,
):
    input_file = tmp_path / "test.tex"
    output_dir = tmp_path / "out"
    config = make_split_config(Granularity.subsection)

    write_directory({Path("test.tex"): LATEX_WITH_SUBSECTION}, tmp_path)
    run_split(input_file, output_dir, config)
    mutate_output(output_dir)

    with pytest.raises(SystemExit):
        run_validate(output_dir / "test.tex", config)

    captured = capsys.readouterr()
    assert expected_error in captured.err
