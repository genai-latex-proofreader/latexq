import re
from pathlib import Path

import pytest

from lq.latex_interface.data_model import LatexContent
from lq.query import (
    InvalidBareTypeError,
    InvalidBracketError,
    InvalidScopeError,
    InvertedRangeError,
    LatexQueryText,
    MissingLabelError,
    NonQueryableDirectLabelError,
    NoSelectableContainerError,
    QueryError,
    QueryOutputMode,
    render_query_from_latex,
)

QUERY_ERROR_DOC: LatexContent = (
    Path(__file__).parent / "latex" / "test_query_errors.tex"
).read_text()


@pytest.mark.parametrize(
    "output_mode",
    [
        pytest.param("fragment", id="fragment"),
        pytest.param("latex", id="latex"),
    ],
)
@pytest.mark.parametrize(
    ("query_text", "error_type", "message_contains"),
    [
        pytest.param(
            "@sec:missing",
            MissingLabelError,
            "Missing label 'sec:missing'.",
            id="missing-label",
        ),
        pytest.param(
            "@sec:3..@sec:1",
            InvertedRangeError,
            "Inverted range '@sec:3..@sec:1'.",
            id="inverted-range",
        ),
        pytest.param(
            "sec",
            InvalidBareTypeError,
            "Invalid bare type 'sec'.",
            id="invalid-bare-type",
        ),
        pytest.param(
            "*sec[l50]",
            InvalidBracketError,
            "Invalid bracket '[l50]'.",
            id="invalid-bracket",
        ),
        pytest.param(
            "@sec:1/@sec:3",
            InvalidScopeError,
            "Invalid scope '/'.",
            id="invalid-scope",
        ),
        pytest.param(
            "@eq:1a",
            NonQueryableDirectLabelError,
            "Label 'eq:1a' exists but is not queryable through the direct-label selector family.",
            id="existing-non-queryable-direct-label",
        ),
    ],
)
def test_query_error_cases(
    output_mode: QueryOutputMode,
    query_text: LatexQueryText,
    error_type: type[Exception],
    message_contains: str,
):
    with pytest.raises(error_type, match=re.escape(message_contains)):
        render_query_from_latex(
            QUERY_ERROR_DOC,
            query_text,
            output_mode,
        )


@pytest.mark.parametrize(
    "output_mode",
    [
        pytest.param("fragment", id="fragment"),
        pytest.param("latex", id="latex"),
    ],
)
@pytest.mark.parametrize(
    ("query_text", "message_contains"),
    [
        pytest.param(
            "@@frontmatter:dedication",
            "Label 'frontmatter:dedication' exists but lies outside all selectable section and subsection content for '@@label'.",
            id="outside-document-structure-before-maketitle",
        ),
        pytest.param(
            "@@main:preface",
            "Label 'main:preface' exists but lies outside all selectable section and subsection content for '@@label'.",
            id="outside-document-structure-in-prematter",
        ),
    ],
)
def test_query_error_e7_cases_for_existing_labels_outside_selectable_content(
    output_mode: QueryOutputMode,
    query_text: LatexQueryText,
    message_contains: str,
):
    with pytest.raises(NoSelectableContainerError, match=re.escape(message_contains)):
        render_query_from_latex(
            QUERY_ERROR_DOC,
            query_text,
            output_mode,
        )


@pytest.mark.parametrize(
    "output_mode",
    [
        pytest.param("fragment", id="fragment"),
        pytest.param("latex", id="latex"),
    ],
)
def test_querying_section_after_first_bibliography_fails(
    output_mode: QueryOutputMode,
):
    # Sections after the first bibliography cannot be queried.
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{A section with a bibliography}
\label{sec:one}
Visible text

\bibliography{refs}

\section{A section after the first bibliography}
\label{sec:two}
Hidden text

\begin{thebibliography}{9}
\bibitem{ref} Ref
\end{thebibliography}

\end{document}"""

    with pytest.raises(QueryError, match=re.escape("sec:two")):
        render_query_from_latex(
            input_latex,
            "@sec:two",
            output_mode,
        )
