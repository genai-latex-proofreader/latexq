from pathlib import Path

from lq.config import LatexqConfig, save_config
from lq.split.data_model import Granularity, SplitConfig
from lq.utils.io import ensure_path_exists, read_directory

from ....utils import assert_output_files, run_lq_cli

LATEX_WITHOUT_APPENDIX = r"""\documentclass{article}
\begin{document}
\begin{abstract}
An abstract.
\end{abstract}
\maketitle
\section{Introduction}
\label{sec:intro}
Hello World!
\section{Methods}
\label{sec:methods}
Some methods.
\end{document}"""

LATEX_WITH_SUBSECTION = r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
\section{Introduction}
\label{sec:intro}
Intro text.
\subsection{Background}
\label{sec:bg}
Background text.
\section{Methods}
\label{sec:methods}
Methods text.
\end{document}"""


def make_split_config(granularity: Granularity) -> LatexqConfig:
    return LatexqConfig(
        split=SplitConfig(
            granularity=granularity,
            main_sections_dir="sections",
            appendix_sections_dir="appendix",
        )
    )


def run_split(
    input_file: Path,
    output_dir: Path,
    config: LatexqConfig,
) -> None:
    config_file = input_file.parent / "lq.yaml"
    save_config(config, config_file)
    run_lq_cli(
        "split",
        "--input-file",
        str(input_file),
        "--output-dir",
        str(output_dir),
        "--config-file",
        str(config_file),
    )


def run_validate(
    input_file: Path,
    config: LatexqConfig,
) -> None:
    config_file = input_file.parent / "lq.yaml"
    save_config(config, config_file)
    run_lq_cli(
        "split",
        "--input-file",
        str(input_file),
        "--config-file",
        str(config_file),
        "--validate",
    )


def _run_flatten(input_file: Path, output_file: Path) -> None:
    run_lq_cli(
        "flatten",
        "--input-file",
        str(input_file),
        "--output-file",
        str(output_file),
    )


def _read_output_texts(output_dir: Path) -> dict[Path, str]:
    return {
        path: content.decode("utf-8")
        for path, content in read_directory(output_dir).items()
    }


def assert_split_output(
    tmp_path: Path,
    input_latex: str,
    granularity: Granularity,
    expected_files: dict[Path, str],
) -> None:
    """Assert split is stable under workflow compositions.

    These checks stay black-box: they only compare emitted files.

    Verified compositions:
    - split(input) == expected
    - split(split(input)) == expected
    - split(flatten(split(input))) == expected
    - split(flatten(flatten(input))) == expected
    - split(flatten(input)) == expected
    """

    def write_main_file(project_dir: Path, latex: str) -> Path:
        input_file = project_dir / "test.tex"
        ensure_path_exists(input_file).write_text(latex)
        return input_file

    def split(input_file: Path, output_dir: Path) -> tuple[Path, dict[Path, str]]:
        run_split(input_file, output_dir, make_split_config(granularity))
        return output_dir / "test.tex", _read_output_texts(output_dir)

    def flatten(input_file: Path, output_dir: Path) -> Path:
        output_file = output_dir / "test.tex"
        _run_flatten(input_file, ensure_path_exists(output_file))
        return output_file

    input_file = write_main_file(tmp_path / "input", input_latex)

    split_main_file, split_output_files = split(input_file, tmp_path / "split")
    assert_output_files(split_output_files, expected_files)

    _, split_split_output_files = split(split_main_file, tmp_path / "split_split")
    assert_output_files(split_split_output_files, expected_files)

    _, split_flatten_split_output_files = split(
        flatten(split_main_file, tmp_path / "flatten_split_input"),
        tmp_path / "split_flatten_split",
    )
    assert_output_files(split_flatten_split_output_files, expected_files)

    _, split_flatten_flatten_input_output_files = split(
        flatten(
            flatten(input_file, tmp_path / "flatten_input_once"),
            tmp_path / "flatten_input_twice",
        ),
        tmp_path / "split_flatten_flatten_input",
    )
    assert_output_files(split_flatten_flatten_input_output_files, expected_files)

    _, split_flatten_input_output_files = split(
        flatten(input_file, tmp_path / "flatten_input"),
        tmp_path / "split_flatten_input",
    )
    assert_output_files(split_flatten_input_output_files, expected_files)
