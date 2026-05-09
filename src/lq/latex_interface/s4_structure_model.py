from dataclasses import dataclass
from enum import Enum

from lq.latex_interface.data_model import LatexLabel
from lq.latex_interface.s1_source import LatexSourceSpan


class LatexStructuralCommandKind(str, Enum):
    begin_document = "begin_document"
    end_document = "end_document"
    maketitle = "maketitle"
    appendix = "appendix"
    section = "section"
    subsection = "subsection"
    bibliography = "bibliography"


@dataclass(frozen=True)
class LatexStructuralCommand:
    kind: LatexStructuralCommandKind
    span: LatexSourceSpan
    title: str | None


class LatexStructuralBlockKind(str, Enum):
    pre_section = "pre_section"
    section = "section"
    subsection = "subsection"


@dataclass(frozen=True)
class LatexStructuralBlock:
    kind: LatexStructuralBlockKind
    in_appendix: bool
    heading_span: LatexSourceSpan | None
    content_span: LatexSourceSpan
    title: str | None
    label: LatexLabel | None
    all_labels: frozenset[LatexLabel]

    def __post_init__(self) -> None:
        if self.kind is LatexStructuralBlockKind.pre_section:
            if self.heading_span is not None:
                raise ValueError("pre_section blocks cannot have a heading_span")
            if self.title is not None:
                raise ValueError("pre_section blocks cannot have a title")
            if self.label is not None:
                raise ValueError("pre_section blocks cannot have a label")
            if self.all_labels:
                raise ValueError("pre_section blocks cannot have all_labels")
            return

        if self.heading_span is None:
            raise ValueError("section and subsection blocks must have a heading_span")
        if self.title is None:
            raise ValueError("section and subsection blocks must have a title")


@dataclass(frozen=True)
class LatexStructuralDocument:
    pre_matter_span: LatexSourceSpan
    begin_document_span: LatexSourceSpan
    blocks: tuple[LatexStructuralBlock, ...]
    bibliography_span: LatexSourceSpan
    post_document_span: LatexSourceSpan
    all_source_labels: frozenset[LatexLabel]
    commands: tuple[LatexStructuralCommand, ...]
