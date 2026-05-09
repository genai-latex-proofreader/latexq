from lq.graph import ExtractedReference, extract_references


def test_extract_supported_single_label_references():
    content = r"""
See \ref{sec:intro}.
See \eqref{eq:main}.
See \vref{sec:related}.
See \autoref{sec:methods}.
See \pageref{sec:results}.
See \nameref{sec:discussion}.
See \cref{sub:proof}.
See \Cref{sub:overview}.
"""

    assert extract_references(content) == (
        ExtractedReference(referenced_label="sec:intro"),
        ExtractedReference(referenced_label="eq:main"),
        ExtractedReference(referenced_label="sec:related"),
        ExtractedReference(referenced_label="sec:methods"),
        ExtractedReference(referenced_label="sec:results"),
        ExtractedReference(referenced_label="sec:discussion"),
        ExtractedReference(referenced_label="sub:proof"),
        ExtractedReference(referenced_label="sub:overview"),
    )


def test_extract_references_supports_vref_and_multi_label_cref_and_c_ref():
    content = r"""
% \ref{sec:commented}
See \vref{sec:supported}.
See \cref{sec:intro,sec:methods}.
See \Cref{sec:alpha, sec:beta}.
See \ref{sec:kept}.
"""

    assert extract_references(content) == (
        ExtractedReference(referenced_label="sec:supported"),
        ExtractedReference(referenced_label="sec:intro"),
        ExtractedReference(referenced_label="sec:methods"),
        ExtractedReference(referenced_label="sec:alpha"),
        ExtractedReference(referenced_label="sec:beta"),
        ExtractedReference(referenced_label="sec:kept"),
    )


def test_extract_references_recurses_into_group_content():
    content = r"""
\caption{See \ref{sec:intro} and \cref{sec:methods,sec:results}.}
"""

    assert extract_references(content) == (
        ExtractedReference(referenced_label="sec:intro"),
        ExtractedReference(referenced_label="sec:methods"),
        ExtractedReference(referenced_label="sec:results"),
    )
