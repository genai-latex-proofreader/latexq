import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from lq.latex_interface.data_model import LatexContent
from lq.query import LatexQueryText, MissingLabelError, render_query_from_latex

QUERY_LATEX_DOCUMENT = (
    Path(__file__).parent / "latex" / "test_latex_queries.tex"
).read_text()


@dataclass(frozen=True)
class LatexQueryCase:
    query_text: LatexQueryText
    expected_output: LatexContent


LATEX_QUERY_CASES = (
    # Selecting all *sections* is not the same as selecting every structural node:
    # *subsection nodes* are not included unless they are selected separately.
    LatexQueryCase(
        query_text="*sec",
        # output should include the input document, with one subsection removed
        expected_output=QUERY_LATEX_DOCUMENT.replace(
            r"""\subsection{Auxiliary}
\label{app:sub:aux}
Auxiliary text

""",
            "",
        ),
    ),
    # Select all sections and subsections
    LatexQueryCase(
        query_text="*sec *sub",
        expected_output=QUERY_LATEX_DOCUMENT,
    ),
    # An empty query in latex mode should preserve only the wrappers and bibliography.
    #
    # Note: this includes no main-body or appendix preface matter.
    LatexQueryCase(
        query_text="",
        expected_output=r"""\documentclass{article}
\usepackage{amsmath}

\begin{document}
\begin{abstract}
Abstract text
\end{abstract}

\maketitle
\begin{thebibliography}{9}
\bibitem{ref} Ref
\end{thebibliography}

\end{document}
""",
    ),
)


@pytest.mark.parametrize("case", LATEX_QUERY_CASES)
def test_latex_query_examples(case: LatexQueryCase):
    latex_output = render_query_from_latex(
        QUERY_LATEX_DOCUMENT,
        case.query_text,
        "latex",
    )

    assert latex_output == case.expected_output


def test_main_body_selection_does_not_include_appendix_switch():
    latex_output = render_query_from_latex(
        QUERY_LATEX_DOCUMENT,
        "@sec:intro",
        "latex",
    )

    assert r"\appendix" not in latex_output


def test_appendix_section_selection_includes_appendix_switch():
    # selecting an appendix section should include \appendix in output
    latex_output = render_query_from_latex(
        QUERY_LATEX_DOCUMENT,
        "@app:sec:proofs",
        "latex",
    )

    assert r"\appendix" in latex_output


def test_bare_app_selection_includes_appendix_switch():
    latex_output = render_query_from_latex(
        QUERY_LATEX_DOCUMENT,
        "app",
        "latex",
    )

    assert r"\appendix" in latex_output


def test_querying_a_commented_out_label_raises_missing_label_error():
    with pytest.raises(
        MissingLabelError,
        match=re.escape("Missing label 'sec:intro'."),
    ):
        render_query_from_latex(
            QUERY_LATEX_DOCUMENT.replace(
                r"\label{sec:intro}",
                r"%\label{sec:intro}",
                1,
            ),
            "@sec:intro",
            "latex",
        )


def test_querying_a_label_with_leading_text_still_works():
    latex_output = render_query_from_latex(
        QUERY_LATEX_DOCUMENT.replace(
            r"\label{sec:intro}",
            r"intro prefix text \label{sec:intro}",
            1,
        ),
        "@sec:intro",
        "latex",
    )

    assert r"\section{Intro}" in latex_output
    assert r"intro prefix text \label{sec:intro}" in latex_output
