import pytest

from lq.latex_interface.data_model import (
    LatexBlock,
    LatexContent,
    LatexStructuralBlock,
)
from lq.query import (
    SECTION_TRUNCATION_NOTICE,
    SUBSECTION_TRUNCATION_NOTICE,
    RenderModifier,
    render_structural_node,
)
from lq.query.s6_node_renderer import iter_paragraphs

SECTION_NOTICE = SECTION_TRUNCATION_NOTICE.rstrip("\n")
SUBSECTION_NOTICE = SUBSECTION_TRUNCATION_NOTICE.rstrip("\n")


def _make_section_node(
    title: str,
    body: LatexContent,
) -> LatexStructuralBlock:
    return LatexBlock.section(
        in_appendix=False,
        content=rf"\section{{{title}}}" + body,
    )


def _make_subsection_node(
    title: str,
    body: LatexContent,
) -> LatexStructuralBlock:
    return LatexBlock.subsection(
        in_appendix=False,
        content=rf"\subsection{{{title}}}" + body,
    )


@pytest.mark.parametrize(
    "preview_paragraph_limit",
    [
        None,
        RenderModifier(preview_paragraph_limit=100),
        RenderModifier(preview_paragraph_limit=2),
        RenderModifier(preview_paragraph_limit=1),
    ],
)
def test_render_structural_node_keeps_full_body_when_preview_limit_matches_body(
    preview_paragraph_limit: RenderModifier | None,
):
    rendered = render_structural_node(
        _make_section_node(
            title="Results",
            body=r"""
\label{sec:results}

The main contribution of this chapter...
Continues in the same paragraph.

Further detail
""",
        ),
        preview_paragraph_limit,
    )

    if preview_paragraph_limit in {
        RenderModifier(preview_paragraph_limit=100),
        RenderModifier(preview_paragraph_limit=2),
        None,
    }:
        expected = r"""\section{Results}
\label{sec:results}

The main contribution of this chapter...
Continues in the same paragraph.

Further detail
"""
    elif preview_paragraph_limit == RenderModifier(preview_paragraph_limit=1):
        expected = r"""\section{Results}
\label{sec:results}

The main contribution of this chapter...
Continues in the same paragraph.

<SECTION_NOTICE>
""".replace("<SECTION_NOTICE>", SECTION_NOTICE)
    else:
        expected = r"""\section{Results}
    \label{sec:results}

<SECTION_NOTICE>
""".replace("<SECTION_NOTICE>", SECTION_NOTICE)

    assert rendered == expected


def test_render_structural_node_treats_comment_lines_inside_paragraph_as_content():
    rendered = render_structural_node(
        _make_section_node(
            title="Results",
            body="""% reviewer note 1
Visible text
More text
% reviewer note 2

% another comment 3
Second paragraph
""",
        ),
        RenderModifier(preview_paragraph_limit=1),
    )

    assert (
        rendered
        == r"""\section{Results}% reviewer note 1
Visible text
More text
% reviewer note 2

<SECTION_NOTICE>
""".replace("<SECTION_NOTICE>", SECTION_NOTICE)
    )


def test_render_structural_node_preserves_leading_structural_label_when_truncating():
    rendered = render_structural_node(
        _make_section_node(
            title="Results",
            body=r"""
\label{sec:results}

First paragraph line

Second paragraph line
""",
        ),
        RenderModifier(preview_paragraph_limit=1),
    )

    assert (
        rendered
        == r"""\section{Results}
\label{sec:results}

First paragraph line

<SECTION_NOTICE>
""".replace("<SECTION_NOTICE>", SECTION_NOTICE)
    )
    assert r"\label{sec:results}" in rendered


def test_render_structural_node_with_p0_keeps_heading_and_direct_label_for_sections_and_subsections():
    section_render = render_structural_node(
        _make_section_node(
            title="Results",
            body=r"""
\label{sec:results}
Visible text
""",
        ),
        RenderModifier(preview_paragraph_limit=0),
    )
    subsection_render = render_structural_node(
        _make_subsection_node(
            title="Auxiliary",
            body=r"""
\label{sub:aux}
Visible text
""",
        ),
        RenderModifier(preview_paragraph_limit=0),
    )

    assert (
        section_render
        == r"""\section{Results}
\label{sec:results}

<SECTION_NOTICE>
""".replace("<SECTION_NOTICE>", SECTION_NOTICE)
    )
    assert (
        subsection_render
        == r"""\subsection{Auxiliary}
\label{sub:aux}

<SUBSECTION_NOTICE>
""".replace("<SUBSECTION_NOTICE>", SUBSECTION_NOTICE)
    )


def test_render_structural_node_reattaches_late_direct_label_exactly_once_when_truncating():
    rendered = render_structural_node(
        _make_subsection_node(
            title="Auxiliary",
            body=r"""
First paragraph

\label{sub:aux}
Second paragraph
""",
        ),
        RenderModifier(preview_paragraph_limit=1),
    )

    assert (
        rendered
        == r"""\subsection{Auxiliary}
First paragraph
\label{sub:aux}

<SUBSECTION_NOTICE>
""".replace("<SUBSECTION_NOTICE>", SUBSECTION_NOTICE)
    )
    assert rendered.count(r"\label{sub:aux}") == 1


def test_render_structural_node_does_not_inject_label_when_extract_already_has_a_label():
    rendered = render_structural_node(
        _make_section_node(
            title="Results",
            body=r"""Visible text
\label{eq:kept}
""",
        ),
        None,
    )

    assert (
        rendered
        == r"""\section{Results}Visible text
\label{eq:kept}
"""
    )
    assert r"\label{sec:results}" not in rendered


def test_iter_paragraphs_splits_paragraphs_on_empty_line_runs():
    lines = [
        "First paragraph\n",
        "still first\n",
        "\n",
        "Second paragraph\n",
    ]

    paragraphs = list(iter_paragraphs(lines))

    assert paragraphs == [
        ["First paragraph\n", "still first\n"],
        ["\n", "Second paragraph\n"],
    ]


def test_iter_paragraphs_keeps_comment_lines_inside_paragraph_content():
    lines = [
        "% reviewer note\n",
        "Visible text\n",
        "\n",
        "Second paragraph\n",
    ]

    paragraphs = list(iter_paragraphs(lines))

    assert paragraphs == [
        ["% reviewer note\n", "Visible text\n"],
        ["\n", "Second paragraph\n"],
    ]


def test_iter_paragraphs_treats_comment_only_lines_inside_separator_as_separator_prefix():
    lines = [
        "First paragraph\n",
        "\n",
        "% separator comment\n",
        "\n",
        "Second paragraph\n",
    ]

    paragraphs = list(iter_paragraphs(lines))

    assert paragraphs == [
        ["First paragraph\n"],
        ["\n", "% separator comment\n", "\n", "Second paragraph\n"],
    ]
