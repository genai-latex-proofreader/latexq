from pathlib import Path

from lq.config import LatexqConfig, save_config
from lq.split.data_model import Granularity, SplitConfig
from lq.utils.io import read_directory
from tests.utils import assert_output_files, run_lq_cli


def _make_split_config() -> LatexqConfig:
    return LatexqConfig(
        split=SplitConfig(
            granularity=Granularity.subsection,
            main_sections_dir="sections",
            appendix_sections_dir="appendix",
        )
    )


def _run_split(input_file: Path, output_dir: Path) -> None:
    config_file = input_file.parent / "lq.yaml"
    save_config(_make_split_config(), config_file)
    run_lq_cli(
        "split",
        "--input-file",
        str(input_file),
        "--output-dir",
        str(output_dir),
        "--config-file",
        str(config_file),
    )


def _run_validate(input_file: Path) -> None:
    config_file = input_file.parent / "lq.yaml"
    save_config(_make_split_config(), config_file)
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


LATEX_DOCS_EXAMPLE_WITH_SUBSECTION_AND_APPENDIX = r"""\documentclass{article}
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
Methods overview.
\subsection{Setup}
\label{sec:methods:setup}
Setup details.
\appendix
\section{Proofs}
\label{sec:proofs}
Proof details.
\end{document}"""


def test_split_subsection_granularity_matches_lq_split_docs_example(tmp_path: Path):
    input_file = tmp_path / "paper.tex"
    input_file.write_text(LATEX_DOCS_EXAMPLE_WITH_SUBSECTION_AND_APPENDIX)

    output_dir = tmp_path / "out"
    _run_split(input_file, output_dir)

    assert_output_files(
        _read_output_texts(output_dir),
        {
            Path("paper.tex"): r"""\documentclass{article}
\begin{document}
\begin{abstract}
An abstract.
\end{abstract}
\maketitle
\input{sections/s01_00_sec_intro.tex}
\input{sections/s02_00_sec_methods.tex}
\input{sections/s02_01_sec_methods_setup.tex}
\appendix
\input{appendix/a01_00_sec_proofs.tex}
\end{document}""",
            Path("sections/s01_00_sec_intro.tex"): r"""\section{Introduction}
\label{sec:intro}
Hello World!
""",
            Path("sections/s02_00_sec_methods.tex"): r"""\section{Methods}
\label{sec:methods}
Methods overview.
""",
            Path("sections/s02_01_sec_methods_setup.tex"): r"""\subsection{Setup}
\label{sec:methods:setup}
Setup details.
""",
            Path("appendix/a01_00_sec_proofs.tex"): r"""\section{Proofs}
\label{sec:proofs}
Proof details.
""",
        },
    )


def test_flatten_on_split_output_reproduces_original_input(tmp_path: Path):
    input_file = tmp_path / "paper.tex"
    input_file.write_text(LATEX_DOCS_EXAMPLE_WITH_SUBSECTION_AND_APPENDIX)

    split_output_dir = tmp_path / "out"
    _run_split(input_file, split_output_dir)

    flattened_output_file = tmp_path / "roundtrip.tex"
    _run_flatten(split_output_dir / "paper.tex", flattened_output_file)

    assert (
        flattened_output_file.read_text()
        == LATEX_DOCS_EXAMPLE_WITH_SUBSECTION_AND_APPENDIX
    )


def test_split_validate_on_split_output_matches_lq_split_docs_example(
    tmp_path: Path, capsys
):
    input_file = tmp_path / "paper.tex"
    input_file.write_text(LATEX_DOCS_EXAMPLE_WITH_SUBSECTION_AND_APPENDIX)

    split_output_dir = tmp_path / "out"
    _run_split(input_file, split_output_dir)

    _run_validate(split_output_dir / "paper.tex")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
