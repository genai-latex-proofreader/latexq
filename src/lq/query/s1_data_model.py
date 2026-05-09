from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Literal

from lq.latex_interface.data_model import LatexLabel

LatexQueryText = str
type QueryOutputMode = Literal["fragment", "latex"]


@dataclass(frozen=True)
class SourcePosition:
    """One character position within the query string being parsed."""

    offset: int
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
class SourceSpan:
    """Half-open source range within the query string for diagnostics."""

    start: SourcePosition
    end: SourcePosition

    def __post_init__(self) -> None:
        if self.end.offset < self.start.offset:
            raise ValueError("span end must not precede start")


class QueryExpressionKind(str, Enum):
    direct_label = "direct_label"
    containing_label = "containing_label"
    prefix = "prefix"
    suffix = "suffix"
    range = "range"
    wildcard = "wildcard"
    appendix = "appendix"


class QueryNodeType(str, Enum):
    section = "sec"
    subsection = "sub"


class SelectorScopeKind(str, Enum):
    appendix_only = "/app"
    main_only = "/!app"


@dataclass(frozen=True)
class DirectLabelExpr:
    """AST node for a direct structural label selector like @intro."""

    label: LatexLabel
    span: SourceSpan | None = None

    kind: ClassVar[QueryExpressionKind] = QueryExpressionKind.direct_label


@dataclass(frozen=True)
class ContainingLabelExpr:
    """AST node for a containing-node selector like @@eq:main."""

    label: LatexLabel
    span: SourceSpan | None = None

    kind: ClassVar[QueryExpressionKind] = QueryExpressionKind.containing_label


@dataclass(frozen=True)
class PrefixExpr:
    """AST node for a prefix selector like @..intro."""

    end_label: LatexLabel
    span: SourceSpan | None = None

    kind: ClassVar[QueryExpressionKind] = QueryExpressionKind.prefix


@dataclass(frozen=True)
class SuffixExpr:
    """AST node for a suffix selector like @intro.."""

    start_label: LatexLabel
    span: SourceSpan | None = None

    kind: ClassVar[QueryExpressionKind] = QueryExpressionKind.suffix


@dataclass(frozen=True)
class LabelRangeExpr:
    """AST node for an inclusive labeled range like @a..@b."""

    start_label: LatexLabel
    end_label: LatexLabel
    span: SourceSpan | None = None

    kind: ClassVar[QueryExpressionKind] = QueryExpressionKind.range


@dataclass(frozen=True)
class WildcardExpr:
    """AST node for a wildcard selector such as *sec or *sub."""

    node_type: QueryNodeType
    span: SourceSpan | None = None

    kind: ClassVar[QueryExpressionKind] = QueryExpressionKind.wildcard


@dataclass(frozen=True)
class AppendixExpr:
    """AST node for the special bare appendix selector app."""

    span: SourceSpan | None = None

    kind: ClassVar[QueryExpressionKind] = QueryExpressionKind.appendix


type QueryExpression = (
    DirectLabelExpr
    | ContainingLabelExpr
    | PrefixExpr
    | SuffixExpr
    | LabelRangeExpr
    | WildcardExpr
    | AppendixExpr
)


@dataclass(frozen=True)
class SelectorScope:
    """One selector-local scope filter, currently /app or /!app."""

    kind: SelectorScopeKind
    span: SourceSpan | None = None

    @classmethod
    def appendix_only(cls, span: SourceSpan | None = None) -> "SelectorScope":
        return cls(kind=SelectorScopeKind.appendix_only, span=span)

    @classmethod
    def main_only(cls, span: SourceSpan | None = None) -> "SelectorScope":
        return cls(kind=SelectorScopeKind.main_only, span=span)


@dataclass(frozen=True)
class RenderModifier:
    """Optional render modifier like [p2] attached to one selector."""

    preview_paragraph_limit: int
    span: SourceSpan | None = None

    def __post_init__(self) -> None:
        if self.preview_paragraph_limit < 0:
            raise ValueError("preview_paragraph_limit must be >= 0")


@dataclass(frozen=True)
class Selector:
    """One parsed selector with its expression, scopes, and render modifier."""

    expression: QueryExpression
    scopes: tuple[SelectorScope, ...] = ()
    render_modifier: RenderModifier | None = None
    span: SourceSpan | None = None


@dataclass(frozen=True)
class Query:
    """A full parsed query as an ordered list of selectors."""

    selectors: tuple[Selector, ...]
    span: SourceSpan | None = None


class QueryErrorCode(str, Enum):
    missing_label = "E1"
    inverted_range = "E2"
    invalid_bare_type = "E3"
    invalid_bracket = "E4"
    invalid_scope = "E5"
    non_queryable_direct_label = "E6"
    no_selectable_container = "E7"


class QueryError(Exception):
    """Base class for structured query-language errors."""

    def __init__(
        self,
        code: QueryErrorCode,
        message: str,
        *,
        span: SourceSpan | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.span = span

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"


class QuerySyntaxError(Exception):
    """Structured syntax error for malformed query text outside E1-E7."""

    def __init__(self, message: str, *, span: SourceSpan | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.span = span

    def __str__(self) -> str:
        return self.message


class MissingLabelError(QueryError):
    def __init__(self, label: LatexLabel, *, span: SourceSpan | None = None) -> None:
        self.label = label
        super().__init__(
            QueryErrorCode.missing_label,
            f"Missing label '{label}'.",
            span=span,
        )


class InvertedRangeError(QueryError):
    def __init__(
        self,
        start_label: LatexLabel,
        end_label: LatexLabel,
        *,
        span: SourceSpan | None = None,
    ) -> None:
        self.start_label = start_label
        self.end_label = end_label
        super().__init__(
            QueryErrorCode.inverted_range,
            f"Inverted range '@{start_label}..@{end_label}'.",
            span=span,
        )


class InvalidBareTypeError(QueryError):
    def __init__(self, token: str, *, span: SourceSpan | None = None) -> None:
        self.token = token
        super().__init__(
            QueryErrorCode.invalid_bare_type,
            f"Invalid bare type '{token}'. Only bare 'app' is allowed.",
            span=span,
        )


class InvalidBracketError(QueryError):
    def __init__(self, bracket_text: str, *, span: SourceSpan | None = None) -> None:
        self.bracket_text = bracket_text
        super().__init__(
            QueryErrorCode.invalid_bracket,
            f"Invalid bracket '{bracket_text}'.",
            span=span,
        )


class InvalidScopeError(QueryError):
    def __init__(self, scope_text: str, *, span: SourceSpan | None = None) -> None:
        self.scope_text = scope_text
        super().__init__(
            QueryErrorCode.invalid_scope,
            f"Invalid scope '{scope_text}'.",
            span=span,
        )


class NonQueryableDirectLabelError(QueryError):
    def __init__(self, label: LatexLabel, *, span: SourceSpan | None = None) -> None:
        self.label = label
        super().__init__(
            QueryErrorCode.non_queryable_direct_label,
            (
                f"Label '{label}' exists but is not queryable through the direct-label "
                "selector family."
            ),
            span=span,
        )


class NoSelectableContainerError(QueryError):
    def __init__(self, label: LatexLabel, *, span: SourceSpan | None = None) -> None:
        self.label = label
        super().__init__(
            QueryErrorCode.no_selectable_container,
            (
                f"Label '{label}' exists but lies outside all selectable section and "
                "subsection content for '@@label'."
            ),
            span=span,
        )
