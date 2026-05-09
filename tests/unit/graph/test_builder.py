import pytest

from lq.graph import GraphEdge, GraphNode, build_reference_graph
from lq.graph.data_model import GraphWarning, ReferenceGraph
from lq.latex_interface.parser import parse_from_latex


def test_build_reference_graph_resolves_containing_targets_and_collapses_edges():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Intro}
\label{sec:intro}
In Section \ref{sec:background} we will prove equation \eqref{eq:einstein}.
See \cref{sub:proof}.
See \ref{sec:intro}.

\section{Background}
\label{sec:background}
\label{eq:einstein}
Background text.

\subsection{Proof}
\label{sub:proof}
Proof text.

\end{document}"""

    reference_graph = build_reference_graph(parse_from_latex(input_latex))

    assert reference_graph.nodes == (
        GraphNode(
            node_id="sec:intro",
            parent_node_id=None,
            document_order=0,
            sibling_order=0,
            title="Intro",
            kind="section",
            in_appendix=False,
        ),
        GraphNode(
            node_id="sec:background",
            parent_node_id=None,
            document_order=1,
            sibling_order=1,
            title="Background",
            kind="section",
            in_appendix=False,
        ),
        GraphNode(
            node_id="sub:proof",
            parent_node_id="sec:background",
            document_order=2,
            sibling_order=0,
            title="Proof",
            kind="subsection",
            in_appendix=False,
        ),
    )

    assert reference_graph.edges == (
        GraphEdge(
            source_node_id="sec:intro",
            target_node_id="sec:intro",
            target_referenced_labels=("sec:intro",),
        ),
        GraphEdge(
            source_node_id="sec:intro",
            target_node_id="sec:background",
            target_referenced_labels=("sec:background", "eq:einstein"),
        ),
        GraphEdge(
            source_node_id="sec:intro",
            target_node_id="sub:proof",
            target_referenced_labels=("sub:proof",),
        ),
    )
    assert reference_graph.warnings == ()


def test_build_reference_graph_emits_warning_for_unlabeled_source_node():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Intro}
\label{sec:intro}
Intro text.

\section{Methods}
See \ref{sec:intro}.

\end{document}"""

    reference_graph = build_reference_graph(parse_from_latex(input_latex))

    assert reference_graph == ReferenceGraph(
        nodes=reference_graph.nodes,
        edges=(),
        warnings=(
            GraphWarning(
                code="unlabeled_source_node",
                message="Skipped outgoing references from unlabeled section 'Methods'.",
                source_node_id=None,
                source_node_title="Methods",
                source_node_kind="section",
                referenced_label=None,
                target_node_label=None,
                target_node_title=None,
                target_node_kind=None,
            ),
        ),
    )


def test_build_reference_graph_emits_warning_for_unlabeled_target_node():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Intro}
\label{sec:intro}
See \ref{eq:detail}.

\section{Methods}
\label{sec:methods}
\subsection{Detail}
\emph{Lead-in}
\label{eq:detail}
Detail text.

\end{document}"""

    reference_graph = build_reference_graph(parse_from_latex(input_latex))

    assert reference_graph.warnings == (
        GraphWarning(
            code="unlabeled_target_node",
            message=(
                "Skipped reference 'eq:detail' from sec:intro because its "
                "containing subsection node 'Detail' is unlabeled."
            ),
            source_node_id="sec:intro",
            source_node_title="Intro",
            source_node_kind="section",
            referenced_label="eq:detail",
            target_node_label=None,
            target_node_title="Detail",
            target_node_kind="subsection",
        ),
    )


def test_build_reference_graph_distinguishes_missing_and_non_selectable_labels():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

Preface text.
\label{main:preface}

\section{Intro}
\label{sec:intro}
See \ref{main:preface}.
See \ref{missing:label}.

\end{document}"""

    reference_graph = build_reference_graph(parse_from_latex(input_latex))

    assert reference_graph.warnings == (
        GraphWarning(
            code="reference_label_without_selectable_node",
            message=(
                "Skipped reference 'main:preface' from sec:intro because the "
                "label exists but is outside selectable structural nodes."
            ),
            source_node_id="sec:intro",
            source_node_title="Intro",
            source_node_kind="section",
            referenced_label="main:preface",
            target_node_label=None,
            target_node_title=None,
            target_node_kind=None,
        ),
        GraphWarning(
            code="missing_reference_label",
            message=(
                "Skipped reference 'missing:label' from sec:intro because the "
                "label does not exist in the parsed document."
            ),
            source_node_id="sec:intro",
            source_node_title="Intro",
            source_node_kind="section",
            referenced_label="missing:label",
            target_node_label=None,
            target_node_title=None,
            target_node_kind=None,
        ),
    )


def test_graph_edge_requires_at_least_one_target_referenced_label():
    with pytest.raises(ValueError, match="at least one target label"):
        GraphEdge(
            source_node_id="sec:intro",
            target_node_id="sec:methods",
            target_referenced_labels=(),
        )
