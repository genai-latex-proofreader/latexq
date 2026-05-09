"""Composable LaTeX document generator for roundtrip testing.

Produces document strings whose structure mirrors exactly what ``to_latex()``
emits, guaranteeing byte-exact roundtrip by construction.
"""

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubsectionSpec:
    title: str
    label: str | None
    content_lines: tuple[str, ...]


@dataclass(frozen=True)
class SectionSpec:
    title: str
    label: str | None
    content_lines: tuple[str, ...]
    subsections: tuple[SubsectionSpec, ...] = ()


@dataclass(frozen=True)
class ContentRegion:
    """A region of content — used identically for main body and appendix."""

    pre_section_content: tuple[str, ...]  # lines before first \section
    sections: tuple[SectionSpec, ...] = ()


@dataclass(frozen=True)
class LatexBlueprint:
    """Declarative description of a LaTeX document to generate."""

    pre_matter: str  # \documentclass + packages
    abstract: str  # abstract content (may be empty)
    main_body: ContentRegion | None  # None = no content before \appendix
    appendix: ContentRegion | None  # None = no \appendix command
    bibliography: str  # bibliography block (may be empty)
    post_render: Callable[[str], str] = field(default=lambda s: s)


def _render_region(region: ContentRegion) -> str:
    """Render a ContentRegion into a string matching the block renderer.

    Mirrors data_model._render_blocks() over one region:
    - pre-section content is emitted first
    - each section emits a section heading plus content
    - each subsection emits a subsection heading plus content
    - Parts are concatenated directly
    """
    parts: list[str] = []

    # Pre-section content comes before the first section in the region.
    pre = _body_from_lines(region.pre_section_content)
    parts.append(pre)

    for sec in region.sections:
        if sec.subsections:
            # Section with subsections: section header + pre-subsection content,
            # then each subsection as a separate part.
            sec_content = _section_body(sec)
            parts.append(rf"\section{{{sec.title}}}" + sec_content)
            for sub in sec.subsections:
                sub_content = _subsection_body(sub)
                parts.append(rf"\subsection{{{sub.title}}}" + sub_content)
        else:
            # Section without subsections
            sec_content = _section_body(sec)
            parts.append(rf"\section{{{sec.title}}}" + sec_content)

    return "".join(parts)


def _body_from_lines(lines: tuple[str, ...]) -> str:
    """Render body lines with the boundary newlines used by stored content."""
    if not lines:
        return ""
    return "\n" + "\n".join(lines) + "\n"


def _section_body(sec: SectionSpec) -> str:
    """Build the body text for a section (label + content lines)."""
    lines: list[str] = []
    if sec.label is not None:
        lines.append(rf"\label{{{sec.label}}}")
    lines.extend(sec.content_lines)
    return _body_from_lines(tuple(lines))


def _subsection_body(sub: SubsectionSpec) -> str:
    """Build the body text for a subsection (label + content lines)."""
    lines: list[str] = []
    if sub.label is not None:
        lines.append(rf"\label{{{sub.label}}}")
    lines.extend(sub.content_lines)
    return _body_from_lines(tuple(lines))


def render(blueprint: LatexBlueprint) -> str:
    """Render a blueprint into a complete LaTeX document string.

    Output mirrors ``to_latex()`` exactly: parts concatenated directly.
    """
    parts = [
        blueprint.pre_matter,
        r"\begin{document}",
    ]

    # begin_document content (abstract etc.)
    parts.append(blueprint.abstract)

    parts.append(r"\maketitle")

    # Main body content (None → empty string, same as to_latex with no blocks)
    if blueprint.main_body is not None:
        parts.append(_render_region(blueprint.main_body))
    else:
        parts.append("")

    # Appendix
    if blueprint.appendix is not None:
        parts.append(r"\appendix")
        parts.append(_render_region(blueprint.appendix))

    # Bibliography
    if blueprint.bibliography:
        parts.append(blueprint.bibliography)

    parts.append(r"\end{document}")

    return blueprint.post_render("".join(parts))
