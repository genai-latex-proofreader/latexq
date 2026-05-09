from collections.abc import Sequence

from lq.latex_interface.data_model import (
    LatexBlockKind,
    LatexContent,
    LatexDocument,
    render_latex_document,
)
from lq.query.s1_data_model import QueryOutputMode
from lq.query.s6_node_renderer import render_structural_node
from lq.query.s6_render_resolution import ResolvedRenderDecision


def render_query_output(
    document: LatexDocument,
    resolved_render_decisions: Sequence[ResolvedRenderDecision],
    output_mode: QueryOutputMode,
) -> LatexContent:
    """Render resolved query results in the requested output mode."""
    if output_mode == "fragment":
        return render_query_fragment(resolved_render_decisions)

    if output_mode == "latex":
        return render_query_latex(document, resolved_render_decisions)

    raise ValueError(f"Unsupported output mode: {output_mode!r}")


def render_query_fragment(
    resolved_render_decisions: Sequence[ResolvedRenderDecision],
) -> LatexContent:
    """Render selected structural nodes only, with no document wrappers."""
    return "".join(
        render_structural_node(block, render_modifier)
        for block, render_modifier in resolved_render_decisions
    )


def render_query_latex(
    document: LatexDocument,
    resolved_render_decisions: Sequence[ResolvedRenderDecision],
) -> LatexContent:
    """Render selected nodes inside a full LaTeX document wrapper."""
    main_decisions = tuple(
        decision
        for decision in resolved_render_decisions
        if not decision[0].in_appendix
    )
    appendix_decisions = tuple(
        decision for decision in resolved_render_decisions if decision[0].in_appendix
    )

    main_body = ""
    if main_decisions:
        main_body = _prepend_required_newline_if_needed(
            previous=r"\maketitle",
            content=_get_pre_section_body(document, is_appendix=False)
            + render_query_fragment(main_decisions),
        )

    appendix: LatexContent | None = None
    if appendix_decisions:
        appendix = _prepend_required_newline_if_needed(
            previous=r"\appendix",
            content=_get_pre_section_body(document, is_appendix=True)
            + render_query_fragment(appendix_decisions),
        )
        if not main_body.endswith("\n"):
            main_body += "\n"

    previous_tail_content = r"\maketitle"
    if appendix is not None:
        previous_tail_content = appendix
    elif main_body:
        previous_tail_content = main_body

    bibliography = _prepend_required_newline_if_needed(
        previous=previous_tail_content,
        content=document.bibliography,
    )
    return (
        render_latex_document(
            pre_matter=document.pre_matter,
            begin_document=document.begin_document,
            main_body=main_body,
            appendix=appendix,
            bibliography=bibliography,
            post_document="",
        )
        + "\n"
    )


def _get_pre_section_body(
    document: LatexDocument,
    *,
    is_appendix: bool,
) -> LatexContent:
    for block in document.iter_pre_section_blocks():
        if block.in_appendix is is_appendix:
            assert block.kind is LatexBlockKind.pre_section
            return block.content

    return ""


def _prepend_required_newline_if_needed(
    previous: LatexContent,
    content: LatexContent,
) -> LatexContent:
    if not content:
        return ""

    if not previous.endswith("\n") and not content.startswith("\n"):
        return "\n" + content

    return content
