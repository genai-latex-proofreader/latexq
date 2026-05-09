from dataclasses import dataclass

type LatexSourceText = str


@dataclass(frozen=True)
class LatexSourcePosition:
    """One character position within LaTeX source text."""

    offset: int

    # line and column are derived from offset. Used only for reporting
    line: int
    column: int

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("offset must be >= 0")
        if self.line < 1:
            raise ValueError("line must be >= 1")
        if self.column < 1:
            raise ValueError("column must be >= 1")


@dataclass(frozen=True)
class LatexSourceSpan:
    """Half-open source range within LaTeX source text."""

    start: LatexSourcePosition
    end: LatexSourcePosition

    def __post_init__(self) -> None:
        if self.end.offset < self.start.offset:
            raise ValueError("span end must not precede start")


def slice_latex_source(
    text: LatexSourceText,
    span: LatexSourceSpan,
) -> LatexSourceText:
    """Return the exact source slice covered by *span*."""
    return text[span.start.offset : span.end.offset]
