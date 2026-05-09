from lq.latex_interface.data_model import (
    LatexBlock,
    LatexBlockKind,
    LatexDocument,
    LatexStructuralBlock,
    render_latex_document,
)


def _pre_section_block(*, in_appendix: bool, body: str) -> LatexBlock:
    return LatexBlock.pre_section(
        in_appendix=in_appendix,
        content=body,
    )


def _section_block(
    *,
    in_appendix: bool,
    title: str,
    body: str,
    all_labels: frozenset[str],
) -> LatexBlock:
    return LatexBlock.section(
        in_appendix=in_appendix,
        content=rf"\section{{{title}}}" + body,
        all_labels=all_labels,
    )


def _subsection_block(
    *,
    in_appendix: bool,
    title: str,
    body: str,
    all_labels: frozenset[str],
) -> LatexBlock:
    return LatexBlock.subsection(
        in_appendix=in_appendix,
        content=rf"\subsection{{{title}}}" + body,
        all_labels=all_labels,
    )


def test_document_preserves_blocks_in_document_order():
    doc = LatexDocument(
        pre_matter="",
        begin_document="",
        blocks=(
            _pre_section_block(in_appendix=False, body="\nPreface\n"),
            _section_block(
                in_appendix=False,
                title="Intro",
                body="\nBody\n",
                all_labels=frozenset({"sec:intro", "eq:intro"}),
            ),
            _subsection_block(
                in_appendix=True,
                title="Proof",
                body="\nAppendix body\n",
                all_labels=frozenset({"sub:proof"}),
            ),
        ),
        all_source_labels=frozenset({"sec:intro", "eq:intro", "sub:proof"}),
        bibliography="",
        post_document="",
    )

    assert doc.blocks == (
        _pre_section_block(in_appendix=False, body="\nPreface\n"),
        _section_block(
            in_appendix=False,
            title="Intro",
            body="\nBody\n",
            all_labels=frozenset({"sec:intro", "eq:intro"}),
        ),
        _subsection_block(
            in_appendix=True,
            title="Proof",
            body="\nAppendix body\n",
            all_labels=frozenset({"sub:proof"}),
        ),
    )


def test_document_helpers_filter_blocks_by_part_and_kind():
    blocks = (
        _pre_section_block(in_appendix=False, body="\nFront\n"),
        _section_block(
            in_appendix=False,
            title="Intro",
            body="\nMain\n",
            all_labels=frozenset({"sec:intro"}),
        ),
        _pre_section_block(in_appendix=True, body="\nAppendix front\n"),
        _subsection_block(
            in_appendix=True,
            title="Proof",
            body="\nAppendix body\n",
            all_labels=frozenset({"sub:proof"}),
        ),
    )
    doc = LatexDocument(
        pre_matter="",
        begin_document="",
        blocks=blocks,
        all_source_labels=frozenset({"sec:intro", "sub:proof"}),
        bibliography="",
        post_document="",
    )

    assert doc.blocks == blocks
    assert tuple(doc.iter_blocks()) == blocks
    assert doc.main_blocks() == blocks[:2]
    assert doc.appendix_blocks() == blocks[2:]
    assert tuple(doc.iter_pre_section_blocks()) == (blocks[0], blocks[2])
    assert tuple(doc.iter_structural_blocks()) == (blocks[1], blocks[3])


def test_structural_block_rejects_pre_section_kind():
    try:
        LatexStructuralBlock(
            kind=LatexBlockKind.pre_section,
            in_appendix=False,
            content="",
        )
    except ValueError as exc:
        assert "section or subsection" in str(exc)
    else:
        raise AssertionError("LatexStructuralBlock accepted pre_section kind")


def test_render_latex_document_without_appendix():
    rendered = render_latex_document(
        pre_matter=r"""\documentclass{article}
""",
        begin_document=r"""
\begin{abstract}
Summary
\end{abstract}
""",
        main_body=r"""
\section{Intro}
Body
""",
        appendix=None,
        bibliography="",
        post_document="",
    )

    assert (
        rendered
        == r"""\documentclass{article}
\begin{document}
\begin{abstract}
Summary
\end{abstract}
\maketitle
\section{Intro}
Body
\end{document}"""
    )


def test_render_latex_document_with_appendix():
    rendered = render_latex_document(
        pre_matter=r"""\documentclass{article}
""",
        begin_document="",
        main_body="",
        appendix=r"""
\section{Proofs}
Details
""",
        bibliography=r"""
\bibliography{refs}
""",
        post_document="",
    )

    assert (
        rendered
        == r"""\documentclass{article}
\begin{document}\maketitle\appendix
\section{Proofs}
Details

\bibliography{refs}
\end{document}"""
    )


def test_render_latex_document_preserves_post_document_content():
    rendered = render_latex_document(
        pre_matter=r"""\documentclass{article}
""",
        begin_document="",
        main_body="",
        appendix=None,
        bibliography="",
        post_document="\n% trailing note\n",
    )

    assert (
        rendered
        == r"""\documentclass{article}
\begin{document}\maketitle\end{document}
% trailing note
"""
    )
