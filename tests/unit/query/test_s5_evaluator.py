import pytest

from lq.latex_interface.parser import parse_from_latex
from lq.query import (
    InvertedRangeError,
    MissingLabelError,
    NonQueryableDirectLabelError,
    NoSelectableContainerError,
    build_document_index,
    evaluate_query,
    parse_query,
)

TEST_DOC = r"""\documentclass{article}

\begin{document}
\label{front:doc}

\maketitle

Main setup
\label{main:pre}

\section{Introduction}
\label{sec:intro}
Intro text
\begin{equation}
\label{eq:intro}
x = 1
\end{equation}

\subsection{Details}
\label{sub:details}
More detail
\begin{figure}
\label{fig:details}
\caption{Detail figure}
\end{figure}

\section{Methods}
\label{sec:methods}
\label{sec:methods:later}
Methods text

\appendix

Appendix setup
\label{app:pre}

\section{Proofs}
\label{sec:app:proofs}

\subsection{Auxiliary}
\label{sub:app:aux}
\begin{equation}
\label{eq:app:aux}
y = 2
\end{equation}

\begin{thebibliography}{9}
\bibitem{ref} Ref text
\label{bib:entry}
\end{thebibliography}

\end{document}"""


RANGE_DOC = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Start}
\label{sec:start}
Start text

\section{Middle}
Middle text

\subsection{Inner}
Inner text

\section{End}
\label{sec:end}
End text

\end{document}"""


@pytest.fixture
def document_index():
    return build_document_index(parse_from_latex(TEST_DOC))


def test_evaluate_selector_direct_label_returns_single_structural_node(document_index):
    evaluated = evaluate_query(document_index, parse_query("@sec:intro"))

    assert [block.title for block in evaluated[0].blocks] == ["Introduction"]


@pytest.mark.parametrize(
    ("text", "expected_title"),
    [
        pytest.param("@@sec:intro", "Introduction", id="reflexive-direct-label"),
        pytest.param("@@eq:intro", "Introduction", id="section-level-nested-label"),
        pytest.param("@@fig:details", "Details", id="subsection-level-nested-label"),
    ],
)
def test_evaluate_selector_containing_label_uses_nearest_selectable_container(
    document_index,
    text: str,
    expected_title: str,
):
    evaluated = evaluate_query(document_index, parse_query(text))

    assert [block.title for block in evaluated[0].blocks] == [expected_title]


def test_evaluate_selector_prefix_stays_within_one_structural_part(document_index):
    evaluated = evaluate_query(document_index, parse_query("@..sec:methods"))

    assert [block.title for block in evaluated[0].blocks] == [
        "Introduction",
        "Details",
        "Methods",
    ]


def test_evaluate_selector_suffix_stays_within_appendix(document_index):
    evaluated = evaluate_query(document_index, parse_query("@sec:app:proofs.."))

    assert [block.title for block in evaluated[0].blocks] == [
        "Proofs",
        "Auxiliary",
    ]


def test_evaluate_selector_range_can_cross_from_main_body_into_appendix(document_index):
    evaluated = evaluate_query(
        document_index, parse_query("@sec:methods..@sub:app:aux")
    )

    assert [block.title for block in evaluated[0].blocks] == [
        "Methods",
        "Proofs",
        "Auxiliary",
    ]


def test_evaluate_selector_range_includes_unlabeled_nodes_between_labeled_endpoints():
    index = build_document_index(parse_from_latex(RANGE_DOC))

    evaluated = evaluate_query(index, parse_query("@sec:start..@sec:end"))

    assert [block.title for block in evaluated[0].blocks] == [
        "Start",
        "Middle",
        "Inner",
        "End",
    ]


def test_evaluate_selector_wildcards_and_scopes_filter_locally(document_index):
    section_titles = [
        block.title
        for block in evaluate_query(document_index, parse_query("*sec"))[0].blocks
    ]
    appendix_subsection_titles = [
        block.title
        for block in evaluate_query(document_index, parse_query("*sub/app"))[0].blocks
    ]
    contradictory_scope_titles = [
        block.title
        for block in evaluate_query(document_index, parse_query("*sec/app/!app"))[
            0
        ].blocks
    ]

    assert section_titles == ["Introduction", "Methods", "Proofs"]
    assert appendix_subsection_titles == ["Auxiliary"]
    assert contradictory_scope_titles == []


def test_evaluate_selector_app_returns_all_appendix_nodes(document_index):
    evaluated = evaluate_query(document_index, parse_query("app"))

    assert [block.title for block in evaluated[0].blocks] == [
        "Proofs",
        "Auxiliary",
    ]


def test_collect_selected_nodes_returns_doc_order_union_independent_of_selector_order(
    document_index,
):
    evaluated = evaluate_query(document_index, parse_query("app @sec:intro"))

    assert [block.title for block in evaluated[0].blocks] == [
        "Proofs",
        "Auxiliary",
    ]
    assert [block.title for block in evaluated[1].blocks] == ["Introduction"]
    assert [block.title for block in _selected_blocks(document_index, evaluated)] == [
        "Introduction",
        "Proofs",
        "Auxiliary",
    ]


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("@sec:missing", id="direct"),
        pytest.param("@@sec:missing", id="containing"),
        pytest.param("@..sec:missing", id="prefix"),
        pytest.param("@sec:missing..", id="suffix"),
        pytest.param("@sec:intro..@sec:missing", id="range-end"),
    ],
)
def test_evaluate_selector_raises_e1_for_missing_labels(document_index, text: str):
    with pytest.raises(MissingLabelError):
        evaluate_query(document_index, parse_query(text))


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("@eq:intro", id="direct"),
        pytest.param("@..eq:intro", id="prefix"),
        pytest.param("@eq:intro..", id="suffix"),
        pytest.param("@sec:intro..@eq:intro", id="range"),
    ],
)
def test_evaluate_selector_raises_e6_for_existing_non_queryable_direct_family_labels(
    document_index,
    text: str,
):
    with pytest.raises(NonQueryableDirectLabelError):
        evaluate_query(document_index, parse_query(text))


def test_evaluate_selector_raises_e7_for_existing_label_outside_selectable_content(
    document_index,
):
    with pytest.raises(NoSelectableContainerError):
        evaluate_query(document_index, parse_query("@@front:doc"))


def test_evaluate_selector_raises_e2_for_inverted_ranges(document_index):
    with pytest.raises(InvertedRangeError):
        evaluate_query(document_index, parse_query("@sec:methods..@sec:intro"))


def _selected_blocks(document_index, evaluated_selectors):
    selected_by_identity = {}
    for evaluated_selector in evaluated_selectors:
        for block in evaluated_selector.blocks:
            selected_by_identity.setdefault(id(block), block)

    return tuple(
        block for block in document_index.blocks if id(block) in selected_by_identity
    )
