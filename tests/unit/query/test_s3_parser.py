import pytest

from lq.query.s1_data_model import (
    AppendixExpr,
    ContainingLabelExpr,
    DirectLabelExpr,
    InvalidBareTypeError,
    InvalidScopeError,
    LabelRangeExpr,
    Query,
    PrefixExpr,
    QueryNodeType,
    QuerySyntaxError,
    RenderModifier,
    Selector,
    SelectorScope,
    SuffixExpr,
    WildcardExpr,
)
from lq.query.s3_parser import parse_query


def test_parse_query_returns_empty_query_for_empty_input():
    assert parse_query("") == Query(selectors=(), span=None)


def test_parse_query_parses_direct_selector_with_scope_and_render_modifier():
    query = parse_query("@sec:intro/app[p2]")
    render_modifier = query.selectors[0].render_modifier

    assert render_modifier is not None

    assert query == Query(
        selectors=(
            Selector(
                expression=DirectLabelExpr(
                    label="sec:intro",
                    span=query.selectors[0].expression.span,
                ),
                scopes=(
                    SelectorScope.appendix_only(span=query.selectors[0].scopes[0].span),
                ),
                render_modifier=RenderModifier(
                    preview_paragraph_limit=2,
                    span=render_modifier.span,
                ),
                span=query.selectors[0].span,
            ),
        ),
        span=query.span,
    )


def test_parse_query_parses_selector_separated_by_whitespace_and_comments():
    query = parse_query("@a % note\n@@b")

    assert query == Query(
        selectors=(
            Selector(
                expression=DirectLabelExpr(
                    label="a",
                    span=query.selectors[0].expression.span,
                ),
                span=query.selectors[0].span,
            ),
            Selector(
                expression=ContainingLabelExpr(
                    label="b",
                    span=query.selectors[1].expression.span,
                ),
                span=query.selectors[1].span,
            ),
        ),
        span=query.span,
    )


def test_parse_query_treats_suffix_then_direct_selector_as_two_selectors():
    query = parse_query("@a.. @b")

    assert query == Query(
        selectors=(
            Selector(
                expression=SuffixExpr(
                    start_label="a",
                    span=query.selectors[0].expression.span,
                ),
                span=query.selectors[0].span,
            ),
            Selector(
                expression=DirectLabelExpr(
                    label="b",
                    span=query.selectors[1].expression.span,
                ),
                span=query.selectors[1].span,
            ),
        ),
        span=query.span,
    )


def test_parse_query_treats_adjacent_range_as_one_selector():
    query = parse_query("@a..@b")

    assert query == Query(
        selectors=(
            Selector(
                expression=LabelRangeExpr(
                    start_label="a",
                    end_label="b",
                    span=query.selectors[0].expression.span,
                ),
                span=query.selectors[0].span,
            ),
        ),
        span=query.span,
    )


def test_parse_query_parses_prefix_wildcard_and_app_selectors():
    query = parse_query("@..intro *sub app")

    assert query == Query(
        selectors=(
            Selector(
                expression=PrefixExpr(
                    end_label="intro",
                    span=query.selectors[0].expression.span,
                ),
                span=query.selectors[0].span,
            ),
            Selector(
                expression=WildcardExpr(
                    node_type=QueryNodeType.subsection,
                    span=query.selectors[1].expression.span,
                ),
                span=query.selectors[1].span,
            ),
            Selector(
                expression=AppendixExpr(span=query.selectors[2].expression.span),
                span=query.selectors[2].span,
            ),
        ),
        span=query.span,
    )


@pytest.mark.parametrize("text", ["sec", "sub", "intro"])
def test_parse_query_rejects_bare_identifiers_other_than_app(text: str):
    with pytest.raises(InvalidBareTypeError, match=rf"Invalid bare type '{text}'"):
        parse_query(text)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        pytest.param("*app", "Unsupported wildcard type 'app'", id="wildcard-app"),
        pytest.param("@", "Expected label or '..' after '@'.", id="lonely-at"),
        pytest.param("@@", "Expected label after '@@'.", id="lonely-double-at"),
        pytest.param("@..", "Expected label after '@..'.", id="lonely-prefix"),
        pytest.param(
            "@a..@", "Expected label after '@label..@'.", id="missing-range-end"
        ),
        pytest.param(
            "app@a",
            "Selectors must be separated by whitespace or comments.",
            id="missing-separator",
        ),
    ],
)
def test_parse_query_rejects_malformed_syntax(text: str, message: str):
    with pytest.raises(QuerySyntaxError, match=message):
        parse_query(text)


@pytest.mark.parametrize("text", ["@a/appx", "@a/!appx", "*sec/appx"])
def test_parse_query_propagates_invalid_scope_errors(text: str):
    with pytest.raises(InvalidScopeError):
        parse_query(text)
