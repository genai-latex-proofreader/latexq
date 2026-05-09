from dataclasses import dataclass
from enum import Enum

from lq.latex_interface.s1_source import LatexSourceSpan, LatexSourceText


type LatexTokenName = str


class LatexTokenKind(str, Enum):
    """Low-level token kinds recognized by the LaTeX scanner."""

    text = "text"
    comment = "comment"
    command = "command"
    # A balanced brace-delimited token like {title} or {sec:intro}.
    group = "group"
    # A balanced bracket-delimited token like [short title].
    optional_group = "optional_group"
    begin_environment = "begin_environment"
    end_environment = "end_environment"


@dataclass(frozen=True)
class LatexToken:
    """One LaTeX token with exact source text, span, and optional name."""

    kind: LatexTokenKind
    text: LatexSourceText
    span: LatexSourceSpan
    name: LatexTokenName | None
    argument_spans: tuple[LatexSourceSpan, ...]
