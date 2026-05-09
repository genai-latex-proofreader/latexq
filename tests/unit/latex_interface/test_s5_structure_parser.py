from pathlib import Path
from typing import cast

import pytest

from lq.latex_interface.data_model import LatexStructuralBlock
from lq.latex_interface.s1_source import slice_latex_source
from lq.latex_interface.s4_structure_model import (
    LatexStructuralBlockKind,
    LatexStructuralCommandKind,
)
from lq.latex_interface.s5_structure_parser import (
    parse_from_latex_with_structure_parser,
    parse_latex_from_files_with_structure_parser,
    parse_latex_structure,
)
from lq.utils.io import InMemoryFileReader

TEST_DOC = r"""\documentclass[12pt, a4paper, twoside]{amsart}

\usepackage{mathrsfs}

\parindent = 0cm
\parskip   = .2cm

\title[short-title]{A longer title for the paper}

\begin{document}

\begin{abstract}
An abstract
\end{abstract}

\maketitle

\section{Introduction}
\label{sec:introduction}
Suppose we have $x^2 + y^2 = 1$.

\section{The main theorem}
\label{sec:main:theorem}
Some more text

\section{Conclusions}
\label{sec:conclusions}
\section{More conclusions}
\label{sec:more:conclusions}

\appendix

Appendix intro

\section{Derivation of main equations}
\label{sec:app1}
Appendix section introduction

\begin{proof}
The result follows since $x^2 + y^2 = 1$
\end{proof}

\end{document}"""


def _parse_from_file_map(files: dict[Path, bytes], main_file: Path):
    return parse_latex_from_files_with_structure_parser(
        InMemoryFileReader(files),
        main_file,
        supporting_file_paths=[],
    )


def test_parse_latex_structure_preserves_exact_document_regions():
    input_latex = r"""\documentclass{article}

\begin{document}
\label{front:doc}

\maketitle

Intro text

\section{Main}
\label{sec:main}
Main content

\begin{thebibliography}{9}
\bibitem{ref} Ref text
\end{thebibliography}

\end{document}"""

    structure = parse_latex_structure(input_latex)

    assert (
        slice_latex_source(input_latex, structure.pre_matter_span)
        == r"""\documentclass{article}

"""
    )
    assert (
        slice_latex_source(input_latex, structure.begin_document_span)
        == r"""
\label{front:doc}

"""
    )
    assert slice_latex_source(input_latex, structure.bibliography_span) == (
        r"""\begin{thebibliography}{9}
\bibitem{ref} Ref text
\end{thebibliography}

"""
    )
    assert [block.kind for block in structure.blocks] == [
        LatexStructuralBlockKind.pre_section,
        LatexStructuralBlockKind.section,
    ]


def test_parse_latex_structure_collects_expected_structural_commands():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section[Short]{Main}
\label{sec:main}

\appendix

\begin{thebibliography}{9}
\end{thebibliography}

\end{document}"""

    structure = parse_latex_structure(input_latex)

    assert [command.kind for command in structure.commands] == [
        LatexStructuralCommandKind.begin_document,
        LatexStructuralCommandKind.maketitle,
        LatexStructuralCommandKind.section,
        LatexStructuralCommandKind.appendix,
        LatexStructuralCommandKind.bibliography,
        LatexStructuralCommandKind.end_document,
    ]


def test_s5_structure_parser_keeps_direct_label_rules_and_nested_labels():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Main}
Intro text before the label.
\label{sec:main}

\section{Methods}
\begin{equation}
\label{eq:method}
x = 1
\end{equation}
\label{sec:methods}

\end{document}"""

    doc = parse_from_latex_with_structure_parser(input_latex)

    assert doc.blocks[1].label == "sec:main"
    assert doc.blocks[1].all_labels == frozenset({"sec:main"})
    assert doc.blocks[2].label is None
    assert doc.blocks[2].all_labels == frozenset({"eq:method", "sec:methods"})


def test_s5_structure_parser_treats_unsupported_sectioning_commands_as_content():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\part{Preface}
\section*{Overview}

\section{Main}
\label{sec:main}
Main intro
\subsection*{Ignored detail}
Still section content

\subsection{Detail}
\label{sub:detail}
Detail text
\subsubsection{Lower heading}
Still subsection content

\end{document}"""

    doc = parse_from_latex_with_structure_parser(input_latex)
    section = cast(LatexStructuralBlock, doc.blocks[1])
    subsection = cast(LatexStructuralBlock, doc.blocks[2])

    assert r"\part{Preface}" in doc.blocks[0].content
    assert r"\section*{Overview}" in doc.blocks[0].content
    assert r"\subsection*{Ignored detail}" in section.body
    assert r"\subsubsection{Lower heading}" in subsection.body


def test_s5_structure_parser_ignores_structural_commands_nested_inside_environments():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Main}
\label{sec:main}
\begin{proof}
\section{Nested ignored}
\label{sec:nested}
\subsection{Nested detail}
\label{sub:nested}
\end{proof}

\section{Next}
\label{sec:next}
Next content

\end{document}"""

    doc = parse_from_latex_with_structure_parser(input_latex)
    main_block = cast(LatexStructuralBlock, doc.blocks[1])
    next_block = cast(LatexStructuralBlock, doc.blocks[2])

    assert [block.kind for block in doc.blocks] == [
        LatexStructuralBlockKind.pre_section,
        LatexStructuralBlockKind.section,
        LatexStructuralBlockKind.section,
    ]
    assert main_block.title == "Main"
    assert main_block.label == "sec:main"
    assert main_block.all_labels == frozenset({"sec:main", "sec:nested", "sub:nested"})
    assert r"\section{Nested ignored}" in main_block.body
    assert r"\subsection{Nested detail}" in main_block.body
    assert next_block.title == "Next"
    assert next_block.label == "sec:next"


def test_s5_structure_parser_handles_nested_environments_before_real_subsection_boundary():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Main}
\begin{proof}
\begin{figure}
\subsection{Ignored detail}
\label{sub:ignored}
\end{figure}
\label{prf:nested}
\end{proof}
\subsection{Detail}
\label{sub:detail}
Detail text

\end{document}"""

    doc = parse_from_latex_with_structure_parser(input_latex)
    section = cast(LatexStructuralBlock, doc.blocks[1])
    subsection = cast(LatexStructuralBlock, doc.blocks[2])

    assert [block.kind for block in doc.blocks] == [
        LatexStructuralBlockKind.pre_section,
        LatexStructuralBlockKind.section,
        LatexStructuralBlockKind.subsection,
    ]
    assert section.title == "Main"
    assert section.label is None
    assert section.all_labels == frozenset({"prf:nested", "sub:detail", "sub:ignored"})
    assert r"\subsection{Ignored detail}" in section.body
    assert subsection.title == "Detail"
    assert subsection.label == "sub:detail"
    assert subsection.all_labels == frozenset({"sub:detail"})


def test_s5_structure_parser_rejects_leading_subsection_in_main_body():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\subsection{Early stuff}
Some early content

\section{Main}
\label{sec:main}
Main content

\end{document}"""

    with pytest.raises(ValueError, match=r"main body must begin with \\section"):
        parse_from_latex_with_structure_parser(input_latex)


def test_s5_structure_parser_exposes_all_source_labels():
    input_latex = r"""\documentclass{article}

\begin{document}
\label{front:doc}

\maketitle

Main setup
\label{main:pre}

\section{Intro}
\label{sec:intro}
Intro text
\begin{equation}
\label{eq:intro}
x = 1
\end{equation}

\begin{thebibliography}{9}
\bibitem{ref} Ref text
\label{bib:entry}
\end{thebibliography}

\end{document}"""

    doc = parse_from_latex_with_structure_parser(input_latex)

    assert doc.all_source_labels == frozenset(
        {"front:doc", "main:pre", "sec:intro", "eq:intro", "bib:entry"}
    )


def test_s5_structure_parser_collects_labels_nested_inside_group_content():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Intro}
\label{sec:intro}
\begin{figure}
\caption{Main result \label{fig:main}}
\end{figure}

\end{document}"""

    doc = parse_from_latex_with_structure_parser(input_latex)

    assert doc.all_source_labels == frozenset({"sec:intro", "fig:main"})
    assert doc.blocks[1].all_labels == frozenset({"sec:intro", "fig:main"})


def test_s5_structure_parser_rejects_nested_label_inside_label_argument():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Intro}
\label{foo \label{bar}}

\end{document}"""

    with pytest.raises(
        ValueError,
        match=r"Unsupported nested \\label command inside \\label\{\.\.\.\}",
    ):
        parse_from_latex_with_structure_parser(input_latex)


def test_s5_structure_parser_resolves_included_files():
    files = {
        Path("main.tex"): rb"""\documentclass{article}

\begin{document}

\maketitle

\input{intro}
\input{setup}

\end{document}""",
        Path("intro.tex"): rb"""\section{Introduction}
\label{sec:introduction}
Intro text
""",
        Path("setup.tex"): rb"""\section{Setup}
\label{sec:setup}
Setup text
""",
    }

    doc = _parse_from_file_map(files, Path("main.tex"))

    assert doc == parse_from_latex_with_structure_parser(
        r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:introduction}
Intro text
\section{Setup}
\label{sec:setup}
Setup text

\end{document}"""
    )
