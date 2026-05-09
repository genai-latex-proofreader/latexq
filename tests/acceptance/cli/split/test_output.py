from dataclasses import dataclass
from pathlib import Path

import pytest

from lq.split.data_model import Granularity
from lq.utils.io import read_directory, write_directory

from ....utils import assert_output_files
from .helpers import (
    LATEX_WITH_SUBSECTION,
    LATEX_WITHOUT_APPENDIX,
    assert_split_output,
    make_split_config,
    run_split,
)


@dataclass(frozen=True)
class SplitOutputTestCase:
    case_id: str
    input_latex: str
    granularity: Granularity
    expected_files: dict[Path, str]


@pytest.mark.parametrize(
    "test_case",
    [
        SplitOutputTestCase(
            case_id="section-without-appendix",
            input_latex=LATEX_WITHOUT_APPENDIX,
            granularity=Granularity.section,
            expected_files={
                Path("test.tex"): r"""\documentclass{article}
\begin{document}
\begin{abstract}
An abstract.
\end{abstract}
\maketitle
\input{sections/s01_sec_intro.tex}
\input{sections/s02_sec_methods.tex}
\end{document}""",
                Path("sections/s01_sec_intro.tex"): r"""\section{Introduction}
\label{sec:intro}
Hello World!
""",
                Path("sections/s02_sec_methods.tex"): r"""\section{Methods}
\label{sec:methods}
Some methods.
""",
            },
        ),
        SplitOutputTestCase(
            case_id="section-with-appendix",
            input_latex=r"""\documentclass{article}
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
\appendix
\section{Proofs}
\label{sec:proofs}
Proof details.
\end{document}""",
            granularity=Granularity.section,
            expected_files={
                Path("test.tex"): r"""\documentclass{article}
\begin{document}
\begin{abstract}
An abstract.
\end{abstract}
\maketitle
\input{sections/s01_sec_intro.tex}
\input{sections/s02_sec_methods.tex}
\appendix
\input{appendix/a01_sec_proofs.tex}
\end{document}""",
                Path("sections/s01_sec_intro.tex"): r"""\section{Introduction}
\label{sec:intro}
Hello World!
""",
                Path("sections/s02_sec_methods.tex"): r"""\section{Methods}
\label{sec:methods}
Some methods.
""",
                Path("appendix/a01_sec_proofs.tex"): r"""\section{Proofs}
\label{sec:proofs}
Proof details.
""",
            },
        ),
        SplitOutputTestCase(
            case_id="generated-inputs-start-on-new-lines",
            input_latex=r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
Lead-in text.\section{Introduction}
\label{sec:intro}
Hello World!
\section{Methods}
\label{sec:methods}
Some methods.
\end{document}""",
            granularity=Granularity.section,
            expected_files={
                Path("test.tex"): r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
Lead-in text.
\input{sections/s01_sec_intro.tex}
\input{sections/s02_sec_methods.tex}
\end{document}""",
                Path("sections/s01_sec_intro.tex"): r"""\section{Introduction}
\label{sec:intro}
Hello World!
""",
                Path("sections/s02_sec_methods.tex"): r"""\section{Methods}
\label{sec:methods}
Some methods.
""",
            },
        ),
        SplitOutputTestCase(
            case_id="slug-collisions-stay-unique",
            input_latex=r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
\section{Intro}
\label{sec:Intro}
Hello World!
\section{Methods}
\label{sec:intro}
Some methods.
\end{document}""",
            granularity=Granularity.section,
            expected_files={
                Path("test.tex"): (
                    r"""\documentclass{article}
"""
                    r"\author{Test Author}"
                    "\n"
                    r"""\begin{document}
\maketitle
\input{sections/s01_sec_intro.tex}
\input{sections/s02_sec_intro.tex}
\end{document}"""
                ),
                Path("sections/s01_sec_intro.tex"): r"""\section{Intro}
\label{sec:Intro}
Hello World!
""",
                Path("sections/s02_sec_intro.tex"): r"""\section{Methods}
\label{sec:intro}
Some methods.
""",
            },
        ),
        SplitOutputTestCase(
            case_id="section-granularity-keeps-subsections-inline",
            input_latex=LATEX_WITH_SUBSECTION,
            granularity=Granularity.section,
            expected_files={
                Path("test.tex"): r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
\input{sections/s01_sec_intro.tex}
\input{sections/s02_sec_methods.tex}
\end{document}""",
                Path("sections/s01_sec_intro.tex"): r"""\section{Introduction}
\label{sec:intro}
Intro text.
\subsection{Background}
\label{sec:bg}
Background text.
""",
                Path("sections/s02_sec_methods.tex"): r"""\section{Methods}
\label{sec:methods}
Methods text.
""",
            },
        ),
        SplitOutputTestCase(
            case_id="subsection-basic",
            input_latex=LATEX_WITH_SUBSECTION,
            granularity=Granularity.subsection,
            expected_files={
                Path("test.tex"): r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
\input{sections/s01_00_sec_intro.tex}
\input{sections/s01_01_sec_bg.tex}
\input{sections/s02_00_sec_methods.tex}
\end{document}""",
                Path("sections/s01_00_sec_intro.tex"): r"""\section{Introduction}
\label{sec:intro}
Intro text.
""",
                Path("sections/s01_01_sec_bg.tex"): r"""\subsection{Background}
\label{sec:bg}
Background text.
""",
                Path("sections/s02_00_sec_methods.tex"): r"""\section{Methods}
\label{sec:methods}
Methods text.
""",
            },
        ),
        SplitOutputTestCase(
            case_id="subsection-with-appendix",
            input_latex=r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
\section{Introduction}
\label{sec:intro}
Intro text.
\subsection{Background}
\label{sec:bg}
Background text.
\appendix
\section{Proofs}
\label{sec:proofs}
Proof text.
\subsection{Extra Proof}
\label{sec:extraproof}
Extra proof text.
\end{document}""",
            granularity=Granularity.subsection,
            expected_files={
                Path("test.tex"): r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
\input{sections/s01_00_sec_intro.tex}
\input{sections/s01_01_sec_bg.tex}
\appendix
\input{appendix/a01_00_sec_proofs.tex}
\input{appendix/a01_01_sec_extraproof.tex}
\end{document}""",
                Path("sections/s01_00_sec_intro.tex"): r"""\section{Introduction}
\label{sec:intro}
Intro text.
""",
                Path("sections/s01_01_sec_bg.tex"): r"""\subsection{Background}
\label{sec:bg}
Background text.
""",
                Path("appendix/a01_00_sec_proofs.tex"): r"""\section{Proofs}
\label{sec:proofs}
Proof text.
""",
                Path("appendix/a01_01_sec_extraproof.tex"): r"""\subsection{Extra Proof}
\label{sec:extraproof}
Extra proof text.
""",
            },
        ),
        SplitOutputTestCase(
            case_id="subsection-counter-resets-per-section",
            input_latex=r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
\section{Introduction}
\label{sec:intro}
Intro text.
\subsection{Background}
\label{sec:bg}
Background text.
\subsection{Scope}
\label{sec:scope}
Scope text.
\section{Methods}
\label{sec:methods}
Methods text.
\subsection{Setup}
\label{sec:setup}
Setup text.
\end{document}""",
            granularity=Granularity.subsection,
            expected_files={
                Path("test.tex"): r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
\input{sections/s01_00_sec_intro.tex}
\input{sections/s01_01_sec_bg.tex}
\input{sections/s01_02_sec_scope.tex}
\input{sections/s02_00_sec_methods.tex}
\input{sections/s02_01_sec_setup.tex}
\end{document}""",
                Path("sections/s01_00_sec_intro.tex"): r"""\section{Introduction}
\label{sec:intro}
Intro text.
""",
                Path("sections/s01_01_sec_bg.tex"): r"""\subsection{Background}
\label{sec:bg}
Background text.
""",
                Path("sections/s01_02_sec_scope.tex"): r"""\subsection{Scope}
\label{sec:scope}
Scope text.
""",
                Path("sections/s02_00_sec_methods.tex"): r"""\section{Methods}
\label{sec:methods}
Methods text.
""",
                Path("sections/s02_01_sec_setup.tex"): r"""\subsection{Setup}
\label{sec:setup}
Setup text.
""",
            },
        ),
        SplitOutputTestCase(
            case_id="subsection-supports-unlabeled-section",
            input_latex=r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
\section{Intro}
Intro text.
\subsection{Background}
\label{sec:bg}
Background text.
\end{document}""",
            granularity=Granularity.subsection,
            expected_files={
                Path("test.tex"): r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
\input{sections/s01_00.tex}
\input{sections/s01_01_sec_bg.tex}
\end{document}""",
                Path("sections/s01_00.tex"): r"""\section{Intro}
Intro text.
""",
                Path("sections/s01_01_sec_bg.tex"): r"""\subsection{Background}
\label{sec:bg}
Background text.
""",
            },
        ),
        SplitOutputTestCase(
            case_id="subsection-supports-unlabeled-subsection",
            input_latex=r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
\section{Intro}
\label{sec:intro}
Intro text.
\subsection{Background}
Background text.
\end{document}""",
            granularity=Granularity.subsection,
            expected_files={
                Path("test.tex"): r"""\documentclass{article}
\author{Test Author}
\begin{document}
\maketitle
\input{sections/s01_00_sec_intro.tex}
\input{sections/s01_01.tex}
\end{document}""",
                Path("sections/s01_00_sec_intro.tex"): r"""\section{Intro}
\label{sec:intro}
Intro text.
""",
                Path("sections/s01_01.tex"): r"""\subsection{Background}
Background text.
""",
            },
        ),
    ],
    ids=lambda test_case: test_case.case_id,
)
def test_split_output_is_stable(
    tmp_path: Path,
    test_case: SplitOutputTestCase,
):
    assert_split_output(
        tmp_path,
        test_case.input_latex,
        test_case.granularity,
        test_case.expected_files,
    )


def test_split_copies_supporting_files(tmp_path: Path):
    input_file = tmp_path / "test.tex"
    out_dir = tmp_path / "out"

    write_directory(
        {
            Path("test.tex"): r"""\documentclass{article}
\begin{document}
\maketitle
\section{Intro}
\input{tables/data1.tex}
\input{tables/data2.tex}
\end{document}
""",
            Path("tables/data1.tex"): "Data 1 content\n",
            Path("tables/data2.tex"): "Data 2 content\n",
        },
        tmp_path,
    )

    config = make_split_config(Granularity.section)
    config.split.supporting_files = ["tables/*.tex"]

    run_split(input_file, out_dir, config)

    actual_files = {
        path: content.decode("utf-8")
        for path, content in read_directory(out_dir).items()
    }
    assert_output_files(
        actual_files,
        {
            Path("test.tex"): r"""\documentclass{article}
\begin{document}
\maketitle
\input{sections/s01.tex}
\end{document}
""",
            Path("sections/s01.tex"): r"""\section{Intro}
\input{tables/data1.tex}
\input{tables/data2.tex}
""",
            Path("tables/data1.tex"): "Data 1 content\n",
            Path("tables/data2.tex"): "Data 2 content\n",
        },
    )
