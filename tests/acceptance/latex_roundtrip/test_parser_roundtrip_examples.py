import pytest

from lq.latex_interface.data_model import to_latex
from lq.latex_interface.parser import parse_from_latex

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


def _assert_roundtrip(latex_str: str) -> None:
    assert to_latex(parse_from_latex(latex_str)) == latex_str


def test_parser_roundtrips_reference_document() -> None:
    _assert_roundtrip(TEST_DOC)


def test_parser_roundtrips_document_with_standalone_input_lines() -> None:
    input_document = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:intro}
\input{tables/data1.tex}
\input{tables/data2.tex}

\end{document}"""

    _assert_roundtrip(input_document)


@pytest.mark.parametrize("include_appendix", [True, False])
def test_parser_roundtrips_minimal_document(include_appendix: bool) -> None:
    minimal_doc = r"""\documentclass[12pt]{amsart}

\title{A longer title for the paper}

\begin{document}

\maketitle

\end{document}"""

    if include_appendix:
        minimal_doc = minimal_doc.replace(
            r"\end{document}", r"\appendix" + "\n...\n" + r"\end{document}"
        )

    _assert_roundtrip(minimal_doc)


def _make_bibliography_fixtures() -> list[str]:
    return [
        r"\bibliography" + "\n...",
        r"\begin{thebibliography}{9}" + "\n...\n" + r"\end{thebibliography}",
        "",
    ]


@pytest.mark.parametrize("bibliography_contents", _make_bibliography_fixtures())
def test_parser_roundtrips_optional_bibliography(bibliography_contents: str) -> None:
    test_doc = TEST_DOC.replace(
        r"\end{document}",
        bibliography_contents + "\n" + r"\end{document}",
    )
    _assert_roundtrip(test_doc)


def test_parser_roundtrips_post_document_content() -> None:
    _assert_roundtrip(TEST_DOC + "\n% trailing comment\n")


def test_parser_roundtrips_section_with_optional_short_title() -> None:
    input_document = r"""\documentclass{article}

\begin{document}

\maketitle

\section[Short]{Main section}
Body text.

\end{document}"""

    _assert_roundtrip(input_document)
