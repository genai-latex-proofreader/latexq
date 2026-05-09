import re

import pytest

from lq.query.s1_data_model import (
    InvalidBracketError,
    InvalidScopeError,
    QuerySyntaxError,
    SourcePosition,
    SourceSpan,
)
from lq.query.s2_tokenizer import QueryToken, QueryTokenKind, tokenize_query


def tokenize_query_checked(text: str) -> tuple[QueryToken, ...]:
    tokens = tokenize_query(text)

    assert "".join(token.text for token in tokens) == text

    return tokens


def test_tokenize_query_returns_no_tokens_for_empty_input():
    assert tokenize_query_checked("") == ()


def test_tokenize_query_returns_comment_token_for_comment_only_input():
    assert tokenize_query_checked("% trailing") == (
        QueryToken(
            kind=QueryTokenKind.comment,
            text="% trailing",
            span=SourceSpan(
                start=SourcePosition(offset=0, line=1, column=1),
                end=SourcePosition(offset=10, line=1, column=11),
            ),
        ),
    )


def test_tokenize_query_recognizes_core_tokens():
    tokens = tokenize_query_checked(
        "@@proof @..end @start.. @a..@b *sec app [p12] /app /!app"
    )

    assert [token.kind for token in tokens] == [
        QueryTokenKind.double_at,
        QueryTokenKind.identifier,
        QueryTokenKind.whitespace,
        QueryTokenKind.at,
        QueryTokenKind.dot_dot,
        QueryTokenKind.identifier,
        QueryTokenKind.whitespace,
        QueryTokenKind.at,
        QueryTokenKind.identifier,
        QueryTokenKind.dot_dot,
        QueryTokenKind.whitespace,
        QueryTokenKind.at,
        QueryTokenKind.identifier,
        QueryTokenKind.dot_dot,
        QueryTokenKind.at,
        QueryTokenKind.identifier,
        QueryTokenKind.whitespace,
        QueryTokenKind.star,
        QueryTokenKind.identifier,
        QueryTokenKind.whitespace,
        QueryTokenKind.identifier,
        QueryTokenKind.whitespace,
        QueryTokenKind.preview,
        QueryTokenKind.whitespace,
        QueryTokenKind.scope_app,
        QueryTokenKind.whitespace,
        QueryTokenKind.scope_not_app,
    ]


def test_tokenize_query_returns_expected_token_objects_for_simple_input():
    assert tokenize_query_checked("@@proof /app\n[p12]") == (
        QueryToken(
            kind=QueryTokenKind.double_at,
            text="@@",
            span=SourceSpan(
                start=SourcePosition(offset=0, line=1, column=1),
                end=SourcePosition(offset=2, line=1, column=3),
            ),
        ),
        QueryToken(
            kind=QueryTokenKind.identifier,
            text="proof",
            span=SourceSpan(
                start=SourcePosition(offset=2, line=1, column=3),
                end=SourcePosition(offset=7, line=1, column=8),
            ),
        ),
        QueryToken(
            kind=QueryTokenKind.whitespace,
            text=" ",
            span=SourceSpan(
                start=SourcePosition(offset=7, line=1, column=8),
                end=SourcePosition(offset=8, line=1, column=9),
            ),
        ),
        QueryToken(
            kind=QueryTokenKind.scope_app,
            text="/app",
            span=SourceSpan(
                start=SourcePosition(offset=8, line=1, column=9),
                end=SourcePosition(offset=12, line=1, column=13),
            ),
        ),
        QueryToken(
            kind=QueryTokenKind.whitespace,
            text="\n",
            span=SourceSpan(
                start=SourcePosition(offset=12, line=1, column=13),
                end=SourcePosition(offset=13, line=2, column=1),
            ),
        ),
        QueryToken(
            kind=QueryTokenKind.preview,
            text="[p12]",
            span=SourceSpan(
                start=SourcePosition(offset=13, line=2, column=1),
                end=SourcePosition(offset=18, line=2, column=6),
            ),
        ),
    )


def test_tokenize_query_allows_single_dot_inside_label_text():
    tokens = tokenize_query_checked("@sec.v1..@sec.v2")

    assert [token.kind for token in tokens] == [
        QueryTokenKind.at,
        QueryTokenKind.identifier,
        QueryTokenKind.dot_dot,
        QueryTokenKind.at,
        QueryTokenKind.identifier,
    ]
    assert tokens[1].text == "sec.v1"
    assert tokens[4].text == "sec.v2"


def test_tokenize_query_preserves_comments_as_separators():
    tokens = tokenize_query_checked("@a % one\n@@b% two")

    assert [token.kind for token in tokens] == [
        QueryTokenKind.at,
        QueryTokenKind.identifier,
        QueryTokenKind.whitespace,
        QueryTokenKind.comment,
        QueryTokenKind.double_at,
        QueryTokenKind.identifier,
        QueryTokenKind.comment,
    ]
    assert tokens[3].text == "% one\n"
    assert tokens[6].text == "% two"


def test_tokenize_query_tracks_line_and_column_positions():
    tokens = tokenize_query_checked("@a\n  *sub")
    star_token = tokens[3]
    identifier_token = tokens[4]

    assert star_token.kind is QueryTokenKind.star
    assert star_token.span.start.offset == 5
    assert star_token.span.start.line == 2
    assert star_token.span.start.column == 3
    assert identifier_token.span.start.line == 2
    assert identifier_token.span.start.column == 4


def test_tokenize_query_accepts_trailing_eof_comment():
    tokens = tokenize_query_checked("@a % trailing")

    assert tokens[-1].kind is QueryTokenKind.comment
    assert tokens[-1].text == "% trailing"


@pytest.mark.parametrize(
    ("text", "expected_scope_text", "expected_start_offset", "expected_end_offset"),
    [
        pytest.param("@a/foo", "/foo", 2, 6, id="named-scope"),
        pytest.param("@a/", "/", 2, 3, id="truncated-eof"),
        pytest.param("@a/appx", "/appx", 2, 7, id="scope-app-prefix-only"),
        pytest.param("@a/!appx", "/!appx", 2, 8, id="scope-not-app-prefix-only"),
    ],
)
def test_tokenize_query_rejects_invalid_scope(
    text: str,
    expected_scope_text: str,
    expected_start_offset: int,
    expected_end_offset: int,
):
    with pytest.raises(
        InvalidScopeError,
        match=rf"Invalid scope '{expected_scope_text}'",
    ) as exc_info:
        tokenize_query(text)

    assert exc_info.value.scope_text == expected_scope_text
    assert exc_info.value.span is not None
    assert exc_info.value.span.start.offset == expected_start_offset
    assert exc_info.value.span.end.offset == expected_end_offset


@pytest.mark.parametrize(
    ("text", "expected_bracket_text", "expected_start_offset", "expected_end_offset"),
    [
        pytest.param("@a[px]", "[px]", 2, 6, id="wrong-body"),
        pytest.param("@a[p12", "[p12", 2, 6, id="missing-closing-bracket"),
    ],
)
def test_tokenize_query_rejects_invalid_bracket(
    text: str,
    expected_bracket_text: str,
    expected_start_offset: int,
    expected_end_offset: int,
):
    with pytest.raises(
        InvalidBracketError,
        match=rf"Invalid bracket '{re.escape(expected_bracket_text)}'",
    ) as exc_info:
        tokenize_query(text)

    assert exc_info.value.bracket_text == expected_bracket_text
    assert exc_info.value.span is not None
    assert exc_info.value.span.start.offset == expected_start_offset
    assert exc_info.value.span.end.offset == expected_end_offset


def test_tokenize_query_rejects_unexpected_character():
    with pytest.raises(
        QuerySyntaxError, match=r"Unexpected character '\}'"
    ) as exc_info:
        tokenize_query("@a}")

    assert exc_info.value.span is not None
    assert exc_info.value.span.start.offset == 2
    assert exc_info.value.span.end.offset == 3
