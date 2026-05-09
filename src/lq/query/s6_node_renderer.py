from collections.abc import Iterable, Iterator

from lq.latex_interface.data_model import (
    LatexBlockKind,
    LatexContent,
    LatexLabel,
    LatexStructuralBlock,
)
from lq.latex_interface.s6_content_helpers import (
    content_has_any_label,
    split_leading_label_command,
)
from lq.query.s1_data_model import QueryNodeType, RenderModifier
from lq.utils.splitters import split_leading

SECTION_TRUNCATION_NOTICE = "(lq: the rest of this section has been truncated)\n"
SUBSECTION_TRUNCATION_NOTICE = "(lq: the rest of this subsection has been truncated)\n"


def render_structural_node(
    block: LatexStructuralBlock,
    render_modifier: RenderModifier | None,
) -> LatexContent:
    """Render one selected structural node, optionally applying preview logic."""
    if render_modifier is None:
        return block.content

    node_type = _node_type_of(block)
    assert block.heading_source is not None

    return block.heading_source + _render_node_body(
        block.body,
        block.label,
        node_type,
        render_modifier,
    )


def _node_type_of(block: LatexStructuralBlock) -> QueryNodeType:
    if block.kind is LatexBlockKind.section:
        return QueryNodeType.section
    if block.kind is LatexBlockKind.subsection:
        return QueryNodeType.subsection
    raise ValueError("pre_section blocks are not selectable structural nodes")


def _render_node_body(
    content: LatexContent,
    label: LatexLabel | None,
    node_type: QueryNodeType,
    render_modifier: RenderModifier | None,
) -> LatexContent:
    if render_modifier is None:
        body = content
        truncation_marker = None
    else:
        body, truncation_marker = _truncate_node_body(
            content,
            node_type,
            render_modifier.preview_paragraph_limit,
        )

    if label is not None and not content_has_any_label(body):
        body = _append_label(body, label)

    if truncation_marker is None:
        return body

    return _append_truncation_marker(body, truncation_marker)


def _truncate_node_body(
    content: LatexContent,
    node_type: QueryNodeType,
    preview_paragraph_limit: int,
) -> tuple[LatexContent, LatexContent | None]:
    if preview_paragraph_limit < 0:
        raise ValueError("preview_paragraph_limit must be >= 0")

    leading_label_prefix, remaining_content = _split_leading_direct_label(content)
    truncated_body = _truncate_body_after_paragraphs(
        remaining_content,
        preview_paragraph_limit,
    )
    if truncated_body == remaining_content:
        return content, None

    return (
        leading_label_prefix + truncated_body,
        _build_truncation_notice(node_type),
    )


def _build_truncation_notice(node_type: QueryNodeType) -> LatexContent:
    if node_type is QueryNodeType.section:
        return SECTION_TRUNCATION_NOTICE

    return SUBSECTION_TRUNCATION_NOTICE


def _append_truncation_marker(
    content: LatexContent,
    truncation_marker: LatexContent,
) -> LatexContent:
    if not content:
        return truncation_marker

    if not content.endswith("\n"):
        content += "\n"

    return content + "\n" + truncation_marker


def _append_label(content: LatexContent, label: LatexLabel) -> LatexContent:
    if content and not content.endswith("\n"):
        content += "\n"

    return content + rf"\label{{{label}}}" + "\n"


def _truncate_body_after_paragraphs(
    content: LatexContent, paragraph_limit: int
) -> LatexContent:
    if paragraph_limit == 0:
        return ""

    paragraphs = list(iter_paragraphs(content.splitlines(keepends=True)))
    if len(paragraphs) <= paragraph_limit:
        return content

    return "".join("".join(paragraph) for paragraph in paragraphs[:paragraph_limit])


def iter_paragraphs(
    lines: Iterable[LatexContent],
) -> Iterator[list[LatexContent]]:
    """Yield paragraph slices that preserve the separator prefix introducing them."""
    paragraph: list[LatexContent] = []
    separator_prefix: list[LatexContent] = []
    pending_comments: list[LatexContent] = []
    after_empty_line = False

    def _is_blank_source_line(line: LatexContent) -> bool:
        return line.strip() == ""

    def _is_comment_only_line(line: LatexContent) -> bool:
        return line.lstrip().startswith("%")

    for line in lines:
        if _is_blank_source_line(line):
            if paragraph:
                yield paragraph
                paragraph = []

            separator_prefix.extend(pending_comments)
            pending_comments = []
            separator_prefix.append(line)
            after_empty_line = True
            continue

        if after_empty_line and _is_comment_only_line(line):
            pending_comments.append(line)
            continue

        if after_empty_line:
            paragraph = separator_prefix + pending_comments + [line]
            separator_prefix = []
            pending_comments = []
            after_empty_line = False
            continue

        paragraph.append(line)

    if paragraph:
        yield paragraph


def _split_leading_direct_label(
    content: LatexContent,
) -> tuple[LatexContent, LatexContent]:
    leading_blank_lines, remaining_content = _split_leading_blank_lines(content)
    label_prefix, remaining_after_label = _split_leading_top_level_label(
        remaining_content
    )
    return leading_blank_lines + label_prefix, remaining_after_label


def _split_leading_blank_lines(
    content: LatexContent,
) -> tuple[LatexContent, LatexContent]:
    leading_lines, remaining_lines = split_leading(
        content.splitlines(keepends=True),
        lambda line: line.strip() == "",
    )

    return "".join(leading_lines), "".join(remaining_lines)


def _split_leading_top_level_label(
    content: LatexContent,
) -> tuple[LatexContent, LatexContent]:
    return split_leading_label_command(content)
