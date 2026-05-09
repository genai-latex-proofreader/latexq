import pytest

from lq.latex_interface.data_model import LatexBlockKind
from lq.latex_interface.parser import parse_from_latex
from lq.query import (
    DocumentIndex,
    build_document_index,
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


def test_build_document_index_tracks_blocks_in_document_order():
    document = parse_from_latex(TEST_DOC)
    index = build_document_index(document)

    assert [block.title for block in index.blocks] == [
        "Introduction",
        "Details",
        "Methods",
        "Proofs",
        "Auxiliary",
    ]
    assert [block.kind for block in index.blocks] == [
        LatexBlockKind.section,
        LatexBlockKind.subsection,
        LatexBlockKind.section,
        LatexBlockKind.section,
        LatexBlockKind.subsection,
    ]


def test_build_document_index_exposes_main_and_appendix_boundaries():
    document = parse_from_latex(TEST_DOC)
    index = build_document_index(document)

    assert index == DocumentIndex(
        blocks=tuple(document.iter_structural_blocks()),
        all_source_labels=frozenset(
            {
                "front:doc",
                "main:pre",
                "sec:intro",
                "eq:intro",
                "sub:details",
                "fig:details",
                "sec:methods",
                "sec:methods:later",
                "app:pre",
                "sec:app:proofs",
                "sub:app:aux",
                "eq:app:aux",
                "bib:entry",
            }
        ),
    )


def test_build_document_index_separates_direct_and_containing_label_lookup():
    document = parse_from_latex(TEST_DOC)
    index = build_document_index(document)

    assert index.direct_label_lookup["sec:intro"].title == "Introduction"
    assert index.direct_label_lookup["sub:details"].title == "Details"
    assert index.direct_label_lookup["sec:app:proofs"].title == "Proofs"

    assert index.containing_label_lookup["sec:intro"].title == "Introduction"
    assert index.containing_label_lookup["eq:intro"].title == "Introduction"
    assert index.containing_label_lookup["fig:details"].title == "Details"
    assert index.containing_label_lookup["sec:methods:later"].title == "Methods"
    assert index.containing_label_lookup["eq:app:aux"].title == "Auxiliary"


def test_build_document_index_tracks_all_source_labels_including_non_selectable_content():
    document = parse_from_latex(TEST_DOC)
    index = build_document_index(document)

    assert index.all_source_labels == frozenset(
        {
            "front:doc",
            "main:pre",
            "sec:intro",
            "eq:intro",
            "sub:details",
            "fig:details",
            "sec:methods",
            "sec:methods:later",
            "app:pre",
            "sec:app:proofs",
            "sub:app:aux",
            "eq:app:aux",
            "bib:entry",
        }
    )
    assert "front:doc" not in index.containing_label_lookup
    assert "main:pre" not in index.containing_label_lookup
    assert "app:pre" not in index.containing_label_lookup
    assert "bib:entry" not in index.containing_label_lookup


def test_build_document_index_uses_nearest_selectable_container_for_nested_labels():
    document = parse_from_latex(TEST_DOC)
    index = build_document_index(document)

    assert index.containing_label_lookup["sub:details"].title == "Details"
    assert index.containing_label_lookup["fig:details"].title == "Details"
    assert index.containing_label_lookup["sub:app:aux"].title == "Auxiliary"
    assert index.containing_label_lookup["eq:app:aux"].title == "Auxiliary"


def test_build_document_index_caches_derived_views():
    document = parse_from_latex(TEST_DOC)
    index = build_document_index(document)

    assert index.direct_label_lookup is index.direct_label_lookup
    assert index.containing_label_lookup is index.containing_label_lookup
    assert index.section_blocks is index.section_blocks
    assert index.subsection_blocks is index.subsection_blocks
    assert index.main_blocks is index.main_blocks
    assert index.appendix_blocks is index.appendix_blocks


def test_build_document_index_exposes_immutable_lookup_mappings():
    document = parse_from_latex(TEST_DOC)
    index = build_document_index(document)

    with pytest.raises(TypeError):
        index.direct_label_lookup["sec:new"] = index.blocks[0]

    with pytest.raises(TypeError):
        index.containing_label_lookup["eq:new"] = index.blocks[0]


def test_build_document_index_lookup_mappings_reuse_existing_block_objects():
    block_count = 6
    equations_per_block = 3
    body = "\n".join(
        "\n".join(
            [
                rf"\section{{Section {index}}}",
                rf"\label{{sec:{index}}}",
                *[
                    "\n".join(
                        [
                            r"\begin{equation}",
                            rf"a_{{{index},{equation_index}}} &= {equation_index}",
                            rf"\label{{eq:{index}:{equation_index}}}",
                            r"\end{equation}",
                        ]
                    )
                    for equation_index in range(equations_per_block)
                ],
            ]
        )
        for index in range(block_count)
    )
    document = parse_from_latex(
        "\n".join(
            [
                r"\documentclass{article}",
                "",
                r"\begin{document}",
                r"\maketitle",
                "",
                body,
                r"\end{document}",
            ]
        )
    )
    index = build_document_index(document)

    for block in index.blocks:
        assert block.label is not None and block.label.startswith("sec:")
        assert index.direct_label_lookup[block.label] is block

        # Assert that equation labels in each section point to the same block for that
        # section. So, we are not copying blocks for each label in memory. This ensures
        # that blocks are not duplicated. This is important to know for larger
        # documents.
        for label in block.all_labels:
            assert index.containing_label_lookup[label] is block


def test_build_document_index_ignores_commented_out_labels():
    input_latex = r"""\documentclass{article}

\begin{document}
% \label{front:commented}

\maketitle

% \label{main:commented}

\section{Introduction}
\label{sec:intro}
Intro text
% \label{sec:commented}

\begin{equation}
\label{eq:intro}
x = 1
\end{equation}

\end{document}"""

    document = parse_from_latex(input_latex)
    index = build_document_index(document)

    assert index.all_source_labels == frozenset({"sec:intro", "eq:intro"})
    assert "front:commented" not in index.all_source_labels
    assert "main:commented" not in index.all_source_labels
    assert "sec:commented" not in index.all_source_labels


def test_build_document_index_points_blocks_at_latex_blocks():
    document = parse_from_latex(TEST_DOC)
    index = build_document_index(document)

    assert all(block.kind is not LatexBlockKind.pre_section for block in index.blocks)
    assert index.blocks == tuple(document.iter_structural_blocks())


def test_build_document_index_prefix_suffix_and_between_follow_document_order():
    document = parse_from_latex(TEST_DOC)
    index = build_document_index(document)

    intro_block = index.direct_label_lookup["sec:intro"]
    methods_block = index.direct_label_lookup["sec:methods"]
    appendix_block = index.direct_label_lookup["sec:app:proofs"]
    aux_block = index.direct_label_lookup["sub:app:aux"]

    assert [block.title for block in index.prefix_through(methods_block)] == [
        "Introduction",
        "Details",
        "Methods",
    ]
    assert [block.title for block in index.suffix_from(appendix_block)] == [
        "Proofs",
        "Auxiliary",
    ]
    assert [block.title for block in index.between(intro_block, aux_block)] == [
        "Introduction",
        "Details",
        "Methods",
        "Proofs",
        "Auxiliary",
    ]
