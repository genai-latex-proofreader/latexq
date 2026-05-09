from dataclasses import dataclass

from lq.query.s1_data_model import (
    AppendixExpr,
    ContainingLabelExpr,
    DirectLabelExpr,
    InvalidBareTypeError,
    LabelRangeExpr,
    LatexQueryText,
    PrefixExpr,
    Query,
    QueryExpression,
    QueryNodeType,
    QuerySyntaxError,
    RenderModifier,
    Selector,
    SelectorScope,
    SourceSpan,
    SuffixExpr,
    WildcardExpr,
)
from lq.query.s2_tokenizer import QueryToken, QueryTokenKind, tokenize_query

_SEPARATOR_TOKEN_KINDS = {
    QueryTokenKind.whitespace,
    QueryTokenKind.comment,
}


@dataclass
class _TokenStream:
    tokens: tuple[QueryToken, ...]
    index: int = 0

    def is_at_end(self) -> bool:
        return self.index >= len(self.tokens)

    def current(self) -> QueryToken:
        return self.tokens[self.index]

    def advance(self) -> QueryToken:
        token = self.tokens[self.index]
        self.index += 1
        return token

    def skip_separators(self) -> bool:
        did_skip = False
        while not self.is_at_end() and self.current().kind in _SEPARATOR_TOKEN_KINDS:
            did_skip = True
            self.advance()
        return did_skip


def parse_query(query_text: LatexQueryText) -> Query:
    """Parse query text into a query AST."""

    return parse_query_tokens(tokenize_query(query_text))


def parse_query_tokens(tokens: tuple[QueryToken, ...]) -> Query:
    """Parse a token sequence into a query AST."""

    stream = _TokenStream(tokens=tokens)
    selectors: list[Selector] = []

    stream.skip_separators()
    while not stream.is_at_end():
        selectors.append(_parse_selector(stream))
        if stream.is_at_end():
            break
        if not stream.skip_separators():
            token = stream.current()
            raise QuerySyntaxError(
                "Selectors must be separated by whitespace or comments.",
                span=token.span,
            )

    if not selectors:
        return Query(selectors=())

    return Query(
        selectors=tuple(selectors),
        span=_combine_spans(selectors[0].span, selectors[-1].span),
    )


def _parse_selector(stream: _TokenStream) -> Selector:
    expression = _parse_expression(stream)
    scopes: list[SelectorScope] = []

    while not stream.is_at_end() and stream.current().kind in {
        QueryTokenKind.scope_app,
        QueryTokenKind.scope_not_app,
    }:
        scopes.append(_parse_scope(stream))

    render_modifier = None
    if not stream.is_at_end() and stream.current().kind is QueryTokenKind.preview:
        render_modifier = _parse_render_modifier(stream)

    selector_end_span = expression.span
    if render_modifier is not None:
        selector_end_span = render_modifier.span
    elif scopes:
        selector_end_span = scopes[-1].span

    return Selector(
        expression=expression,
        scopes=tuple(scopes),
        render_modifier=render_modifier,
        span=_combine_spans(expression.span, selector_end_span),
    )


def _parse_expression(stream: _TokenStream) -> QueryExpression:
    token = stream.current()

    if token.kind is QueryTokenKind.at:
        at_token = stream.advance()
        return _parse_at_expression(stream, at_token)

    if token.kind is QueryTokenKind.double_at:
        double_at_token = stream.advance()
        label_token = _expect_identifier(
            stream,
            "Expected label after '@@'.",
            double_at_token.span,
        )
        return ContainingLabelExpr(
            label=label_token.text,
            span=_combine_spans(double_at_token.span, label_token.span),
        )

    if token.kind is QueryTokenKind.star:
        star_token = stream.advance()
        type_token = _expect_identifier(
            stream,
            "Expected node type after '*'.",
            star_token.span,
        )
        node_type = _parse_node_type(type_token)
        return WildcardExpr(
            node_type=node_type,
            span=_combine_spans(star_token.span, type_token.span),
        )

    if token.kind is QueryTokenKind.identifier:
        identifier_token = stream.advance()
        if identifier_token.text == "app":
            return AppendixExpr(span=identifier_token.span)
        raise InvalidBareTypeError(identifier_token.text, span=identifier_token.span)

    raise QuerySyntaxError(
        f"Unexpected token '{token.text}' at start of selector.",
        span=token.span,
    )


def _parse_at_expression(stream: _TokenStream, at_token: QueryToken) -> QueryExpression:
    if stream.is_at_end():
        raise QuerySyntaxError("Expected label or '..' after '@'.", span=at_token.span)

    next_token = stream.current()

    if next_token.kind is QueryTokenKind.dot_dot:
        dot_dot_token = stream.advance()
        label_token = _expect_identifier(
            stream,
            "Expected label after '@..'.",
            _combine_spans(at_token.span, dot_dot_token.span),
        )
        return PrefixExpr(
            end_label=label_token.text,
            span=_combine_spans(at_token.span, label_token.span),
        )

    label_token = _expect_identifier(
        stream,
        "Expected label after '@'.",
        at_token.span,
    )

    if stream.is_at_end() or stream.current().kind is not QueryTokenKind.dot_dot:
        return DirectLabelExpr(
            label=label_token.text,
            span=_combine_spans(at_token.span, label_token.span),
        )

    dot_dot_token = stream.advance()
    if not stream.is_at_end() and stream.current().kind is QueryTokenKind.at:
        range_at_token = stream.advance()
        end_label_token = _expect_identifier(
            stream,
            "Expected label after '@label..@'.",
            _combine_spans(at_token.span, range_at_token.span),
        )
        return LabelRangeExpr(
            start_label=label_token.text,
            end_label=end_label_token.text,
            span=_combine_spans(at_token.span, end_label_token.span),
        )

    return SuffixExpr(
        start_label=label_token.text,
        span=_combine_spans(at_token.span, dot_dot_token.span),
    )


def _parse_scope(stream: _TokenStream) -> SelectorScope:
    token = stream.advance()
    if token.kind is QueryTokenKind.scope_app:
        return SelectorScope.appendix_only(span=token.span)
    if token.kind is QueryTokenKind.scope_not_app:
        return SelectorScope.main_only(span=token.span)
    raise QuerySyntaxError(f"Unexpected scope token '{token.text}'.", span=token.span)


def _parse_render_modifier(stream: _TokenStream) -> RenderModifier:
    token = stream.advance()
    return RenderModifier(
        preview_paragraph_limit=int(token.text[2:-1]), span=token.span
    )


def _expect_identifier(
    stream: _TokenStream,
    message: str,
    span: SourceSpan | None,
) -> QueryToken:
    if stream.is_at_end() or stream.current().kind is not QueryTokenKind.identifier:
        raise QuerySyntaxError(message, span=span)
    return stream.advance()


def _parse_node_type(token: QueryToken) -> QueryNodeType:
    if token.text == QueryNodeType.section.value:
        return QueryNodeType.section
    if token.text == QueryNodeType.subsection.value:
        return QueryNodeType.subsection
    raise QuerySyntaxError(
        f"Unsupported wildcard type '{token.text}'. Expected 'sec' or 'sub'.",
        span=token.span,
    )


def _combine_spans(
    start_span: SourceSpan | None,
    end_span: SourceSpan | None,
) -> SourceSpan | None:
    if start_span is None:
        return end_span
    if end_span is None:
        return start_span
    return SourceSpan(start=start_span.start, end=end_span.end)
