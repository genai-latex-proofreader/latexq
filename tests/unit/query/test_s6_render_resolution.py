from lq.latex_interface.parser import parse_from_latex
from lq.query import (
    build_document_index,
    evaluate_query,
    parse_query,
    resolve_render_decisions,
)


TEST_DOC = r"""\documentclass{article}

\begin{document}
\maketitle

\section{Introduction}
\label{sec:intro}
Intro text

\section{Methods}
\label{sec:methods}
Methods text

\appendix

\section{Proofs}
\label{sec:app:proofs}
Proof text

\subsection{Auxiliary}
\label{sub:app:aux}
Aux text

\end{document}"""


def test_direct_label_beats_range_for_render_resolution():
    decisions = _resolve("@sec:intro..@sec:methods[p1] @sec:methods[p4]")

    methods_decision = _decision_by_title(decisions)["Methods"]

    assert methods_decision[1] is not None
    assert methods_decision[1].preview_paragraph_limit == 4


def test_scoped_wildcard_beats_unscoped_wildcard():
    decisions = _resolve("*sec[p2] *sec/app[p1]")
    by_title = _decision_by_title(decisions)

    assert by_title["Introduction"][1] is not None
    assert by_title["Introduction"][1].preview_paragraph_limit == 2
    assert by_title["Methods"][1] is not None
    assert by_title["Methods"][1].preview_paragraph_limit == 2
    assert by_title["Proofs"][1] is not None
    assert by_title["Proofs"][1].preview_paragraph_limit == 1


def test_full_render_beats_preview_at_equal_precedence():
    decisions = _resolve("@sec:intro[p2] @sec:intro")

    assert _decision_by_title(decisions)["Introduction"][1] is None


def test_larger_preview_limit_wins_at_equal_precedence():
    decisions = _resolve("*sec[p2] *sec[p4]")

    for title in ["Introduction", "Methods", "Proofs"]:
        render_modifier = _decision_by_title(decisions)[title][1]
        assert render_modifier is not None
        assert render_modifier.preview_paragraph_limit == 4


def test_app_uses_scoped_wildcard_precedence_and_matches_expanded_form():
    app_decisions = _resolve("app[p1] *sec[p3] *sub[p4]")
    expanded_decisions = _resolve("*sec/app[p1] *sub/app[p1] *sec[p3] *sub[p4]")

    assert _decision_signature(app_decisions) == _decision_signature(expanded_decisions)


def _resolve(query_text: str):
    document_index = build_document_index(parse_from_latex(TEST_DOC))
    evaluated = evaluate_query(document_index, parse_query(query_text))
    return resolve_render_decisions(document_index, evaluated)


def _decision_by_title(decisions):
    return {decision[0].title: decision for decision in decisions}


def _decision_signature(decisions):
    return tuple(
        (
            decision[0].title,
            None if decision[1] is None else decision[1].preview_paragraph_limit,
        )
        for decision in decisions
    )
