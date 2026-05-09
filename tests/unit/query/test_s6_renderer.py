from lq.latex_interface.parser import parse_from_latex
from lq.query import (
    SECTION_TRUNCATION_NOTICE,
    build_document_index,
    evaluate_query,
    parse_query,
    render_query_fragment,
    render_query_latex,
    render_query_output,
    resolve_render_decisions,
)

SECTION_NOTICE = SECTION_TRUNCATION_NOTICE.rstrip("\n")

QUERY_RENDER_DOC = r"""\documentclass{article}
\usepackage{amsmath}

\begin{document}
\begin{abstract}
Abstract text
\end{abstract}

\maketitle

Main preface
\label{main:preface}

\section{Intro}
\label{sec:intro}
Intro paragraph one.

Intro paragraph two.

\section{Methods}
\label{sec:methods}
Methods text

\appendix

Appendix preface
\label{app:preface}

\section{Proofs}
\label{sec:app:proofs}
Proof paragraph.

\subsection{Aux}
\label{sub:app:aux}
Aux text

\begin{thebibliography}{9}
\bibitem{ref} Ref
\end{thebibliography}

\end{document}"""


def test_render_query_fragment_emits_only_selected_nodes_in_document_order():
    rendered = render_query_fragment(
        _resolve_render_decisions(QUERY_RENDER_DOC, "app @sec:intro[p1]")
    )

    assert (
        rendered
        == r"""\section{Intro}
\label{sec:intro}
Intro paragraph one.

<SECTION_NOTICE>
\section{Proofs}
\label{sec:app:proofs}
Proof paragraph.

\subsection{Aux}
\label{sub:app:aux}
Aux text

""".replace("<SECTION_NOTICE>", SECTION_NOTICE)
    )
    assert r"\begin{document}" not in rendered
    assert r"\appendix" not in rendered
    assert "Main preface" not in rendered
    assert "Appendix preface" not in rendered
    assert "thebibliography" not in rendered


def test_render_query_latex_includes_only_appendix_wrappers_for_appendix_selection():
    document = parse_from_latex(QUERY_RENDER_DOC)

    rendered = render_query_latex(
        document,
        _resolve_render_decisions(QUERY_RENDER_DOC, "@sec:app:proofs[p1]"),
    )

    assert (
        rendered
        == r"""\documentclass{article}
\usepackage{amsmath}

\begin{document}
\begin{abstract}
Abstract text
\end{abstract}

\maketitle
\appendix

Appendix preface
\label{app:preface}

\section{Proofs}
\label{sec:app:proofs}
Proof paragraph.

\begin{thebibliography}{9}
\bibitem{ref} Ref
\end{thebibliography}

\end{document}
"""
    )
    assert "Main preface" not in rendered
    assert r"\section{Intro}" not in rendered
    assert r"\section{Methods}" not in rendered


def test_render_query_output_latex_preserves_main_and_appendix_wrappers():
    document = parse_from_latex(QUERY_RENDER_DOC)

    rendered = render_query_output(
        document,
        _resolve_render_decisions(QUERY_RENDER_DOC, "@sec:intro @sub:app:aux"),
        output_mode="latex",
    )

    assert (
        rendered
        == r"""\documentclass{article}
\usepackage{amsmath}

\begin{document}
\begin{abstract}
Abstract text
\end{abstract}

\maketitle

Main preface
\label{main:preface}

\section{Intro}
\label{sec:intro}
Intro paragraph one.

Intro paragraph two.

\appendix

Appendix preface
\label{app:preface}

\subsection{Aux}
\label{sub:app:aux}
Aux text

\begin{thebibliography}{9}
\bibitem{ref} Ref
\end{thebibliography}

\end{document}
"""
    )
    assert r"\section{Methods}" not in rendered
    assert r"\section{Proofs}" not in rendered


def test_render_query_output_latex_for_empty_selection_preserves_wrappers_only():
    document = parse_from_latex(QUERY_RENDER_DOC)

    rendered = render_query_output(
        document,
        (),
        output_mode="latex",
    )

    assert (
        rendered
        == r"""\documentclass{article}
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
"""
    )
    assert "Main preface" not in rendered
    assert "Appendix preface" not in rendered
    assert r"\appendix" not in rendered
    assert r"\section{Intro}" not in rendered
    assert r"\section{Proofs}" not in rendered


def _resolve_render_decisions(document_text: str, query_text: str):
    document_index = build_document_index(parse_from_latex(document_text))
    evaluated = evaluate_query(document_index, parse_query(query_text))
    return resolve_render_decisions(document_index, evaluated)
