import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import cast

from lq.latex_interface.s2_scan_model import LatexToken, LatexTokenKind
from lq.latex_interface.s3_scanner import scan_latex

# --- Data model for a parsed LaTeX document ---

# Type alias for LaTeX string labels (e.g. "sec:intro").
LatexLabel = str

# Type alias for LaTeX formatted content.
LatexContent = str


@dataclass(frozen=True)
class ResolvedLatexIncludes:
    r"""Resolved LaTeX include expansion plus label source provenance.

    Attributes:
        expanded_latex: Full LaTeX content after recursively expanding
            ``\input{...}`` directives (except explicitly preserved
            supporting files).
        label_source_files: Mapping of every detected LaTeX label to the
            input file path where that label was detected during include
            expansion. Labels in supporting files are not included here.

    Note:
        Duplicate labels are validated elsewhere in the parsing pipeline.
        This structure preserves the first encountered source path per label.
    """

    expanded_latex: str
    label_source_files: dict[LatexLabel, Path]


SECTION_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9:_.-]+$")
RESERVED_QUERY_LABEL_SUBSTRING = ".."


def _get_direct_section_labels(
    blocks: tuple["LatexBlock", ...],
) -> list[LatexLabel]:
    """Return direct section and subsection labels in document order."""
    return [
        block.label
        for block in blocks
        if block.kind is not LatexBlockKind.pre_section and block.label is not None
    ]


def _get_all_discovered_labels(
    blocks: tuple["LatexBlock", ...],
) -> list[LatexLabel]:
    """Return every parsed LaTeX label seen in selectable structural content."""
    labels: list[LatexLabel] = []
    for block in blocks:
        if block.kind is LatexBlockKind.pre_section:
            continue
        if block.label is not None:
            labels.append(block.label)
        labels.extend(sorted(block.all_labels))
    return labels


def _get_duplicate_label_counts(
    labels: list[LatexLabel],
) -> dict[LatexLabel, int]:
    return {
        label: count for label, count in sorted(Counter(labels).items()) if count > 1
    }


def _raise_for_reserved_query_labels(labels: list[LatexLabel]) -> None:
    """Reject labels that use the query language's reserved substring."""
    reserved_labels = sorted(
        {label for label in labels if RESERVED_QUERY_LABEL_SUBSTRING in label}
    )
    if reserved_labels:
        label_list = ", ".join(reserved_labels)
        message = (
            "Unsupported label" if len(reserved_labels) == 1 else "Unsupported labels"
        )
        raise ValueError(
            f"{message}. The substring '..' is reserved by the query language and "
            f"cannot appear in LaTeX labels: {label_list}"
        )


def _raise_for_duplicate_labels(labels: list[LatexLabel]) -> None:
    """Reject duplicate LaTeX labels and report every duplicated name."""
    duplicate_counts = _get_duplicate_label_counts(labels)
    if duplicate_counts:
        duplicate_labels = ", ".join(
            f"'{label}' (x{count})" for label, count in duplicate_counts.items()
        )
        raise Exception(
            "Duplicate labels detected in LaTeX document. Please fix. "
            f"Duplicate labels: {duplicate_labels}."
        )


def validate_latex_label_content(label: LatexLabel) -> None:
    if r"\label" in label:
        raise ValueError(r"Unsupported nested \label command inside \label{...}.")


def validate_section_labels(
    blocks: tuple["LatexBlock", ...],
) -> None:
    """Validate structural labels stored in ordered structural blocks."""
    labels = _get_direct_section_labels(blocks)
    all_discovered_labels = _get_all_discovered_labels(blocks)

    invalid_labels = [
        label for label in labels if not SECTION_LABEL_PATTERN.fullmatch(label)
    ]
    if invalid_labels:
        label_list = ", ".join(invalid_labels)
        message = (
            "Invalid section label"
            if len(invalid_labels) == 1
            else "Invalid section labels"
        )
        raise ValueError(
            f"{message}. Only letters, digits, ':', '_', '-', and '.' are allowed: {label_list}"
        )

    _raise_for_reserved_query_labels(all_discovered_labels)
    _raise_for_duplicate_labels(labels)


def validate_all_latex_labels(all_discovered_labels: list[LatexLabel]) -> None:
    """Validate global LaTeX label invariants across the full parsed document."""
    _raise_for_reserved_query_labels(all_discovered_labels)
    _raise_for_duplicate_labels(all_discovered_labels)


class LatexBlockKind(str, Enum):
    pre_section = "pre_section"
    section = "section"
    subsection = "subsection"


@dataclass(frozen=True)
class _ParsedStructuralContent:
    heading_source: LatexContent
    title: str
    body: LatexContent
    label: LatexLabel | None


@lru_cache(maxsize=None)
def _parse_structural_content(
    kind: LatexBlockKind,
    content: LatexContent,
) -> _ParsedStructuralContent:
    tokens = scan_latex(content)
    if not tokens:
        raise ValueError("Structural block content must not be empty")

    heading_token = tokens[0]
    if heading_token.kind is not LatexTokenKind.command:
        raise ValueError("Structural block content must start with a heading command")
    if heading_token.name != kind.value:
        raise ValueError(
            f"Expected structural block content to start with \\{kind.value}"
        )

    title = _get_required_group_content(heading_token, content)
    if title is None:
        raise ValueError(
            f"Structural block heading \\{kind.value} must include a title group"
        )

    heading_end_offset = _token_full_end_offset(heading_token)
    body = content[heading_end_offset:]
    return _ParsedStructuralContent(
        heading_source=content[:heading_end_offset],
        title=title,
        body=body,
        label=_find_direct_label_in_content(body),
    )


def _get_required_group_content(
    token: LatexToken,
    content: LatexContent,
) -> str | None:
    for argument_span in token.argument_spans:
        argument_text = content[argument_span.start.offset : argument_span.end.offset]
        if argument_text.startswith("{") and argument_text.endswith("}"):
            label_content = argument_text[1:-1]
            if token.name == "label":
                validate_latex_label_content(label_content)
            return label_content
    return None


def _find_direct_label_in_content(content: LatexContent) -> LatexLabel | None:
    nested_environment_depth = 0

    for token in scan_latex(content):
        if token.kind is LatexTokenKind.begin_environment:
            if nested_environment_depth == 0:
                return None
            nested_environment_depth += 1
            continue

        if token.kind is LatexTokenKind.end_environment:
            if nested_environment_depth > 0:
                nested_environment_depth -= 1
            continue

        if nested_environment_depth != 0:
            continue

        if token.kind in {LatexTokenKind.text, LatexTokenKind.comment}:
            continue

        if token.kind is LatexTokenKind.command and token.name == "label":
            return _get_required_group_content(token, content)

        return None

    return None


def _token_full_end_offset(token: LatexToken) -> int:
    if not token.argument_spans:
        return token.span.end.offset
    return token.argument_spans[-1].end.offset


class LatexBlock:
    r"""Factory namespace and shared behavior for parsed LaTeX blocks."""

    kind: LatexBlockKind
    in_appendix: bool
    content: LatexContent

    @property
    def heading_source(self) -> LatexContent | None:
        r"""Exact original LaTeX heading source for structural nodes, else `None`.

        Examples:
            `\section{Intro}`               -> `\section{Intro}`
            `\section[Short]{Main section}` -> `\section[Short]{Main section}`

            For a LatexPreSectionBlock      -> None
        """
        return None

    @property
    def title(self) -> str | None:
        r"""Normalized semantic title for structural nodes, else `None`.

        This differs from `heading_source`: `\section[Short]{Main section}`
        has `title == "Main section"`.

        Examples:
            `\section{Intro}`                  -> `Intro`
            `\section[Short]{Main section}`    -> `Main section`
            For a LatexPreSectionBlock         -> None`
        """
        return None

    @property
    def label(self) -> LatexLabel | None:
        r"""Direct structural label for selectable nodes, else `None`.

        Examples:
            `\section{Intro}\label{sec:intro}`  -> `sec:intro`

            If the node has no direct label, or for `LatexPreSectionBlock`:
            `label is None`
        """
        return None

    @property
    def all_labels(self) -> frozenset[LatexLabel]:
        r"""Labels attached to the structural node body, else an empty set."""
        return frozenset()

    @property
    def is_selectable_structural_node(self) -> bool:
        """Whether this block is a selectable structural node."""
        return self.kind is not LatexBlockKind.pre_section and self.label is not None

    @classmethod
    def pre_section(
        cls,
        *,
        in_appendix: bool,
        content: LatexContent,
    ) -> "LatexPreSectionBlock":
        return LatexPreSectionBlock(
            in_appendix=in_appendix,
            content=content,
        )

    @classmethod
    def section(
        cls,
        *,
        in_appendix: bool,
        content: LatexContent,
        all_labels: frozenset[LatexLabel] = frozenset(),
    ) -> "LatexStructuralBlock":
        return LatexStructuralBlock(
            kind=LatexBlockKind.section,
            in_appendix=in_appendix,
            content=content,
            _all_labels=all_labels,
        )

    @classmethod
    def subsection(
        cls,
        *,
        in_appendix: bool,
        content: LatexContent,
        all_labels: frozenset[LatexLabel] = frozenset(),
    ) -> "LatexStructuralBlock":
        return LatexStructuralBlock(
            kind=LatexBlockKind.subsection,
            in_appendix=in_appendix,
            content=content,
            _all_labels=all_labels,
        )


@dataclass(frozen=True)
class LatexPreSectionBlock(LatexBlock):
    """A non-structural region before the first section in a document part.

    This can contain labels, for example between `\appendix` and the first
    appendix section. Those labels are preserved globally in
    `LatexDocument.all_source_labels`, but this block intentionally has no
    `all_labels`; lq only attaches labels to selectable structural nodes.

    A pre-section region is not itself addressable as a node.
    """

    in_appendix: bool
    content: LatexContent
    kind: LatexBlockKind = field(init=False, default=LatexBlockKind.pre_section)


@dataclass(frozen=True)
class LatexStructuralBlock(LatexBlock):
    """A selectable section or subsection block with preserved heading source."""

    kind: LatexBlockKind
    in_appendix: bool
    content: LatexContent
    _all_labels: frozenset[LatexLabel] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if self.kind not in {LatexBlockKind.section, LatexBlockKind.subsection}:
            raise ValueError("LatexStructuralBlock kind must be section or subsection")
        _parse_structural_content(self.kind, self.content)

    @property
    def heading_source(self) -> LatexContent:
        return _parse_structural_content(self.kind, self.content).heading_source

    @property
    def title(self) -> str:
        return _parse_structural_content(self.kind, self.content).title

    @property
    def body(self) -> LatexContent:
        """LaTeX content after the structural heading."""
        return _parse_structural_content(self.kind, self.content).body

    @property
    def label(self) -> LatexLabel | None:
        return _parse_structural_content(self.kind, self.content).label

    @property
    def all_labels(self) -> frozenset[LatexLabel]:
        return self._all_labels


@dataclass(frozen=True)
class LatexDocument:
    # --- start of document ---
    pre_matter: LatexContent

    # --- \begin{document} ---

    begin_document: LatexContent

    # Note:
    #   \begin{abstract} ... \end{abstract} is in "begin_document"

    # --- \maketitle ---

    # Ordered structural content blocks, including appendix blocks after main blocks.
    blocks: tuple[LatexBlock, ...]

    # All parsed LaTeX labels seen anywhere in the document, including labels in
    # non-structural regions such as prematter, bibliography, or pre-section
    # appendix text. Those labels are intentionally not attached to a
    # LatexPreSectionBlock because latexq cannot address a pre-section region as a
    # structural node.
    all_source_labels: frozenset[LatexLabel]

    bibliography: LatexContent

    # --- \end{document} ---

    post_document: LatexContent

    # images, bibliography files, etc.
    supporting_files: dict[Path, bytes] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_section_labels(self.blocks)

    def iter_blocks(self) -> Iterator[LatexBlock]:
        return iter(self.blocks)

    def main_blocks(self) -> tuple[LatexBlock, ...]:
        return tuple(block for block in self.blocks if not block.in_appendix)

    def appendix_blocks(self) -> tuple[LatexBlock, ...]:
        return tuple(block for block in self.blocks if block.in_appendix)

    def iter_structural_blocks(self) -> Iterator["LatexStructuralBlock"]:
        return (
            cast(LatexStructuralBlock, block)
            for block in self.blocks
            if block.kind is not LatexBlockKind.pre_section
        )

    def iter_pre_section_blocks(self) -> Iterator["LatexPreSectionBlock"]:
        return (
            cast(LatexPreSectionBlock, block)
            for block in self.blocks
            if block.kind is LatexBlockKind.pre_section
        )


def _render_blocks(
    blocks: tuple[LatexBlock, ...],
) -> Iterator[LatexContent]:
    """Render ordered structural blocks into LaTeX strings."""
    for block in blocks:
        yield block.content


def render_latex_document(
    pre_matter: LatexContent,
    begin_document: LatexContent,
    main_body: LatexContent,
    appendix: LatexContent | None,
    bibliography: LatexContent,
    post_document: LatexContent,
) -> LatexContent:
    """Join rendered document regions around the fixed LaTeX wrapper commands.

    Callers remain responsible for preparing each region, including any needed
    boundary newlines inside ``main_body``, ``appendix``, and ``bibliography``.
    """
    parts = [
        pre_matter,
        r"\begin{document}",
        begin_document,
        r"\maketitle",
        main_body,
    ]

    if appendix is not None:
        parts.append(r"\appendix")
        parts.append(appendix)

    parts.append(bibliography)
    parts.append(r"\end{document}")
    parts.append(post_document)

    return "".join(parts)


def to_latex(obj: LatexDocument) -> str:
    """
    Convert a parsed LaTeX document back into a LaTeX document string.

    Content strings include their boundary newlines so parts are
    concatenated directly.
    """
    appendix_blocks = obj.appendix_blocks()
    appendix = None
    if appendix_blocks:
        appendix = "".join(_render_blocks(appendix_blocks))

    return render_latex_document(
        pre_matter=obj.pre_matter,
        begin_document=obj.begin_document,
        main_body="".join(_render_blocks(obj.main_blocks())),
        appendix=appendix,
        bibliography=obj.bibliography,
        post_document=obj.post_document,
    )
