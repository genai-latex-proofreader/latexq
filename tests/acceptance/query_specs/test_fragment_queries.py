from dataclasses import dataclass
from pathlib import Path

import pytest

from lq.latex_interface.data_model import LatexContent
from lq.query import (
    SECTION_TRUNCATION_NOTICE,
    SUBSECTION_TRUNCATION_NOTICE,
    LatexQueryText,
    render_query_from_latex,
)
from tests.acceptance.query_specs.baseline_document import (
    content_from_fragments,
)

SECTION_NOTICE = SECTION_TRUNCATION_NOTICE.rstrip("\n")
SUBSECTION_NOTICE = SUBSECTION_TRUNCATION_NOTICE.rstrip("\n")

TEST_LATEX_DOCUMENT = (
    Path(__file__).parent / "latex" / "test_fragment_queries.tex"
).read_text()


@dataclass(frozen=True)
class QueryExampleCase:
    queries: list[LatexQueryText]  # each query should produce the expected output
    expected_output: LatexContent


QUERY_EXAMPLE_CASES = (
    # --- Empty query ---
    # Empty query returns nothing.
    QueryExampleCase(
        queries=[
            "",
            "  ",
            "\n",
            "\n   ",
            "   \n",
            "%",
            "%%%",
            "%a%",
            "% empty query comment",
        ],
        expected_output="",
    ),
    # --- Basic direct and containing-label selection ---
    # Direct section selection returns just that section.
    QueryExampleCase(
        queries=["  @sec:1", "@sec:1  ", "@sec:1", "@sec:1 % direct section"],
        expected_output=content_from_fragments("sec:1"),
    ),
    # Direct subsection selection returns just that subsection.
    QueryExampleCase(
        queries=["@sec:1a"],
        expected_output=content_from_fragments("sec:1a"),
    ),
    # Direct subsection selection also works when the direct label comes later.
    QueryExampleCase(
        queries=["@sec:1b"],
        expected_output=content_from_fragments("sec:1b"),
    ),
    # Containing-label lookup resolves to the enclosing subsection for a nested equation label.
    QueryExampleCase(
        queries=["@@eq:1a", "@@eq:1a    % @sec:1b is not selected"],
        expected_output=content_from_fragments("sec:1a"),
    ),
    # Repeating a containing-label selector is idempotent after deduplication.
    QueryExampleCase(
        queries=["@@eq:1a @@eq:1a"],
        expected_output=content_from_fragments("sec:1a"),
    ),
    # Containing-label selection can combine with direct label selection.
    QueryExampleCase(
        queries=[
            "@@eq:1a @sec:1b",
            "@sec:1b @@eq:1a",  # reversed order ok
            "@@eq:1a\n@sec:1b",
            "@@eq:1a % keep containing subsection\n@sec:1b",
        ],
        expected_output=content_from_fragments("sec:1a", "sec:1b"),
    ),
    # Range selection.
    # A range across main-body sections includes unlabeled sections that fall between the endpoints.
    QueryExampleCase(
        queries=["@sec:1..@sec:3"],
        expected_output=content_from_fragments(
            "sec:1",
            "sec:1a",
            "sec:1b",
            "content-of-unlabeled-section-2",
            "sec:3",
        ),
    ),
    # A range within one section covers the contiguous subsection span.
    QueryExampleCase(
        queries=["@sec:1a..@sec:1b"],
        expected_output=content_from_fragments("sec:1a", "sec:1b"),
    ),
    # A main-body prefix selector
    QueryExampleCase(
        queries=["@..sec:1b"],
        expected_output=content_from_fragments("sec:1", "sec:1a", "sec:1b"),
    ),
    # A main-body suffix selector does not cross into the appendix.
    QueryExampleCase(
        queries=["@sec:1a.."],
        expected_output=content_from_fragments(
            "sec:1a",
            "sec:1b",
            "content-of-unlabeled-section-2",
            "sec:3",
        ),
    ),
    # An appendix prefix selector starts at the beginning of the appendix.
    QueryExampleCase(
        queries=["@..app:sec:B1"],
        expected_output=content_from_fragments(
            "app:sec:A",
            "app:sec:B",
            "app:sec:B1",
        ),
    ),
    # An appendix suffix selector runs to the end of the appendix only.
    QueryExampleCase(
        queries=["@app:sec:B1.."],
        expected_output=content_from_fragments("app:sec:B1", "app:sec:B2"),
    ),
    # Preview and scoped selection.
    # A preview modifier keeps only the first paragraph of the section body.
    QueryExampleCase(
        queries=["@sec:1[p1]"],
        expected_output=content_from_fragments(
            "sec:1",
            paragraph_limit=1,
        ),
    ),
    # On a late-label structural node, p0 reattaches the label before truncation.
    QueryExampleCase(
        queries=["@sec:1b[p0]"],
        expected_output=r"""\subsection{Section 1b}
\label{sec:1b}

<SUBSECTION_NOTICE>
""".replace("<SUBSECTION_NOTICE>", SUBSECTION_NOTICE),
    ),
    # On a late-label structural node, p1 keeps the first paragraph then reattaches the label.
    QueryExampleCase(
        queries=["@sec:1b[p1]"],
        expected_output=r"""\subsection{Section 1b}
aaa
\label{sec:1b}

<SUBSECTION_NOTICE>
""".replace("<SUBSECTION_NOTICE>", SUBSECTION_NOTICE),
    ),
    # On the same node, p2 keeps the full body because it has only two paragraphs.
    QueryExampleCase(
        queries=["@sec:1b[p2]"],
        expected_output=content_from_fragments("sec:1b"),
    ),
    # A very large paragraph limit also yields the full node body unchanged.
    QueryExampleCase(
        queries=["@sec:1b[p1000]"],
        expected_output=content_from_fragments("sec:1b"),
    ),
    # Contradictory scope filtering yields an empty result for a main-body section.
    QueryExampleCase(
        queries=["@sec:1/app"],
        expected_output="",
    ),
    # /!app does nothing if the selector only matches content outside the appendix.
    QueryExampleCase(
        queries=["@@eq:1a/!app", "@@eq:1a/!app/!app"],
        expected_output=content_from_fragments("sec:1a"),
    ),
    # A parent section can be previewed while a child subsection stays full.
    QueryExampleCase(
        queries=["@sec:1[p0] @sec:1a"],
        expected_output=content_from_fragments(
            "sec:1",
            paragraph_limit=0,
        )
        + content_from_fragments("sec:1a"),
    ),
    # Direct appendix section selection returns only that appendix section.
    QueryExampleCase(
        queries=["@app:sec:A"],
        expected_output=content_from_fragments("app:sec:A"),
    ),
    # Appendix subsection ranges work entirely within the appendix.
    QueryExampleCase(
        queries=["@app:sec:B1..@app:sec:B2"],
        expected_output=content_from_fragments("app:sec:B1", "app:sec:B2"),
    ),
    # Ranges can cross from the main body into the appendix.
    QueryExampleCase(
        queries=["@sec:1b..@app:sec:B2"],
        expected_output=content_from_fragments(
            "sec:1b",
            "content-of-unlabeled-section-2",
            "sec:3",
            "app:sec:A",
            "app:sec:B",
            "app:sec:B1",
            "app:sec:B2",
        ),
    ),
    # --- Wildcard selection and scope-limited skeletons ---
    # Wildcard p0 on both node types keeps only headings and labels everywhere.
    QueryExampleCase(
        queries=["*sec[p0] *sub[p0]"],
        expected_output=r"""\section{Section 1}
\label{sec:1}

<SECTION_NOTICE>
\subsection{Section 1a}
\label{sec:1a}

<SUBSECTION_NOTICE>
\subsection{Section 1b}
\label{sec:1b}

<SUBSECTION_NOTICE>
\section{Section 2}

<SECTION_NOTICE>
\section{Section 3}
\label{sec:3}

<SECTION_NOTICE>
\section{Section A}
\label{app:sec:A}

<SECTION_NOTICE>
\section{Section B}
\label{app:sec:B}

<SECTION_NOTICE>
\subsection{Section B1}
\label{app:sec:B1}

<SUBSECTION_NOTICE>
\subsection{Section B2}
\label{app:sec:B2}

<SUBSECTION_NOTICE>
""".replace("<SECTION_NOTICE>", SECTION_NOTICE).replace(
            "<SUBSECTION_NOTICE>", SUBSECTION_NOTICE
        ),
    ),
    # Wildcard section p0 keeps only section headings and labels.
    QueryExampleCase(
        queries=["*sec[p0]"],
        expected_output=content_from_fragments(
            "sec:1",
            "content-of-unlabeled-section-2",
            "sec:3",
            "app:sec:A",
            "app:sec:B",
            paragraph_limit=0,
        ),
    ),
    # Wildcard subsection p0 keeps only subsection headings and labels.
    QueryExampleCase(
        queries=["*sub[p0]"],
        expected_output=content_from_fragments(
            "sec:1a",
            "sec:1b",
            "app:sec:B1",
            "app:sec:B2",
            paragraph_limit=0,
        ),
    ),
    # Appendix-only wildcard p0 can be applied to both sections and subsections.
    QueryExampleCase(
        queries=["*sec/app[p0] *sub/app[p0]"],
        expected_output=content_from_fragments(
            "app:sec:A",
            "app:sec:B",
            "app:sec:B1",
            "app:sec:B2",
            paragraph_limit=0,
        ),
    ),
    # Appendix-only wildcard section p0 keeps only appendix section structure.
    QueryExampleCase(
        queries=["*sec/app[p0]"],
        expected_output=content_from_fragments(
            "app:sec:A",
            "app:sec:B",
            paragraph_limit=0,
        ),
    ),
    # Appendix-only wildcard subsection p0 keeps only appendix subsection structure.
    QueryExampleCase(
        queries=["*sub/app[p0]"],
        expected_output=content_from_fragments(
            "app:sec:B1",
            "app:sec:B2",
            paragraph_limit=0,
        ),
    ),
    # Main-only wildcard p0 can be applied to both sections and subsections.
    QueryExampleCase(
        queries=["*sec/!app[p0] *sub/!app[p0]"],
        expected_output=content_from_fragments(
            "sec:1",
            "sec:1a",
            "sec:1b",
            "content-of-unlabeled-section-2",
            "sec:3",
            paragraph_limit=0,
        ),
    ),
    # Main-only wildcard section p0 keeps only main-body section structure.
    QueryExampleCase(
        queries=["*sec/!app[p0]"],
        expected_output=content_from_fragments(
            "sec:1",
            "content-of-unlabeled-section-2",
            "sec:3",
            paragraph_limit=0,
        ),
    ),
    # Main-only wildcard subsection p0 keeps only main-body subsection structure.
    QueryExampleCase(
        queries=["*sub/!app[p0]"],
        expected_output=content_from_fragments(
            "sec:1a",
            "sec:1b",
            paragraph_limit=0,
        ),
    ),
    # Contradictory wildcard scopes produce no result.
    QueryExampleCase(
        queries=[
            "*sec/app/!app",
            "*sec/app/!app/!app/!app",
            "*sec/app/app/app/!app",
            "*sec/app/!app/app/!app",
        ],
        expected_output="",
    ),
    # --- Precedence resolution ---
    # A direct selector overrides wildcard preview for the same subsection.
    QueryExampleCase(
        queries=["*sub[p0] @sec:1a"],
        expected_output=content_from_fragments("sec:1a")
        + content_from_fragments(
            "sec:1b",
            "app:sec:B1",
            "app:sec:B2",
            paragraph_limit=0,
        ),
    ),
    # A direct selector overrides range preview for the same endpoint node.
    QueryExampleCase(
        queries=["@sec:1a..@sec:1b[p0] @sec:1b"],
        expected_output=content_from_fragments(
            "sec:1a",
            paragraph_limit=0,
        )
        + content_from_fragments("sec:1b"),
    ),
    # At equal precedence, the larger preview limit wins.
    QueryExampleCase(
        queries=["@sec:1[p0] @sec:1[p1]"],
        expected_output=content_from_fragments(
            "sec:1",
            paragraph_limit=1,
        ),
    ),
    # At equal precedence, a full direct selection beats a previewed one.
    QueryExampleCase(
        queries=["@sec:1[p1] @sec:1"],
        expected_output=content_from_fragments("sec:1"),
    ),
    # Whole-document p0 can be overridden by more specific subsection selectors.
    QueryExampleCase(
        queries=["*sec[p0] *sub[p0] @sec:1a @app:sec:B1"],
        expected_output=r"""\section{Section 1}
\label{sec:1}

<SECTION_NOTICE>
\subsection{Section 1a}
\label{sec:1a}
aaa

\begin{equation}
x = y  \label{eq:1a}
\end{equation}

bbb
bbb

\subsection{Section 1b}
\label{sec:1b}

<SUBSECTION_NOTICE>
\section{Section 2}

<SECTION_NOTICE>
\section{Section 3}
\label{sec:3}

<SECTION_NOTICE>
\section{Section A}
\label{app:sec:A}

<SECTION_NOTICE>
\section{Section B}
\label{app:sec:B}

<SECTION_NOTICE>
\subsection{Section B1}
\label{app:sec:B1}
appendix subsection b1 aaa

appendix subsection b1 bbb

\subsection{Section B2}
\label{app:sec:B2}

<SUBSECTION_NOTICE>
""".replace("<SECTION_NOTICE>", SECTION_NOTICE).replace(
            "<SUBSECTION_NOTICE>", SUBSECTION_NOTICE
        ),
    ),
    # Appendix shorthands
    QueryExampleCase(
        queries=["app", "app/app"],
        expected_output=content_from_fragments(
            "app:sec:A",
            "app:sec:B",
            "app:sec:B1",
            "app:sec:B2",
        ),
    ),
)


@pytest.mark.parametrize("case", QUERY_EXAMPLE_CASES)
def test_fragment_query_examples(
    case: QueryExampleCase,
):
    for query_text in case.queries:
        fragment_output = render_query_from_latex(
            TEST_LATEX_DOCUMENT,
            query_text,
            "fragment",
        )
        latex_output = render_query_from_latex(
            TEST_LATEX_DOCUMENT,
            query_text,
            "latex",
        )

        assert fragment_output == case.expected_output
        assert len(latex_output) > len(fragment_output)
