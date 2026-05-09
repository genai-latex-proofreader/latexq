from dataclasses import dataclass
from enum import Enum

from lq.query.s1_data_model import (
    InvalidBracketError,
    InvalidScopeError,
    LatexQueryText,
    QuerySyntaxError,
    SourcePosition,
    SourceSpan,
)


class QueryTokenKind(str, Enum):
    """Token kinds recognized by the query tokenizer."""

    at = "@"
    double_at = "@@"
    dot_dot = ".."
    star = "*"
    scope_app = "/app"
    scope_not_app = "/!app"
    preview = "preview"
    identifier = "identifier"
    whitespace = "whitespace"
    comment = "comment"


@dataclass(frozen=True)
class QueryToken:
    """One token from the query string with exact source text and span."""

    kind: QueryTokenKind
    text: str
    span: SourceSpan


@dataclass
class _TokenizerState:
    query_text: LatexQueryText
    offset: int = 0
    line: int = 1
    column: int = 1

    def is_at_end(self) -> bool:
        return self.offset >= len(self.query_text)

    def current(self) -> str:
        return self.query_text[self.offset]

    def startswith(self, value: str) -> bool:
        return self.query_text.startswith(value, self.offset)

    def mark(self) -> SourcePosition:
        return SourcePosition(offset=self.offset, line=self.line, column=self.column)

    def advance(self) -> str:
        char = self.query_text[self.offset]
        self.offset += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def emit(self, kind: QueryTokenKind, start: SourcePosition) -> QueryToken:
        end = self.mark()
        return QueryToken(
            kind=kind,
            text=self.query_text[start.offset : end.offset],
            span=SourceSpan(start=start, end=end),
        )


def tokenize_query(query_text: LatexQueryText) -> tuple[QueryToken, ...]:
    """Tokenize query text, preserving whitespace and comments as separators."""

    state = _TokenizerState(query_text=query_text)
    tokens: list[QueryToken] = []

    while not state.is_at_end():
        char = state.current()
        start = state.mark()

        if char in " \t\n\r":
            while not state.is_at_end() and state.current() in " \t\n\r":
                state.advance()
            tokens.append(state.emit(QueryTokenKind.whitespace, start))
            continue

        if char == "%":
            state.advance()
            while not state.is_at_end() and state.current() != "\n":
                state.advance()
            if not state.is_at_end() and state.current() == "\n":
                state.advance()
            tokens.append(state.emit(QueryTokenKind.comment, start))
            continue

        if state.startswith("@@"):
            state.advance()
            state.advance()
            tokens.append(state.emit(QueryTokenKind.double_at, start))
            continue

        if state.startswith(".."):
            state.advance()
            state.advance()
            tokens.append(state.emit(QueryTokenKind.dot_dot, start))
            continue

        if char == "@":
            state.advance()
            tokens.append(state.emit(QueryTokenKind.at, start))
            continue

        if char == "*":
            state.advance()
            tokens.append(state.emit(QueryTokenKind.star, start))
            continue

        if _matches_exact_scope_token(state, "/!app"):
            for _ in range(len("/!app")):
                state.advance()
            tokens.append(state.emit(QueryTokenKind.scope_not_app, start))
            continue

        if _matches_exact_scope_token(state, "/app"):
            for _ in range(len("/app")):
                state.advance()
            tokens.append(state.emit(QueryTokenKind.scope_app, start))
            continue

        if char == "/":
            invalid_scope = _consume_invalid_scope(state)
            raise InvalidScopeError(
                invalid_scope,
                span=SourceSpan(start=start, end=state.mark()),
            )

        if char == "[":
            if _consume_preview_modifier(state):
                tokens.append(state.emit(QueryTokenKind.preview, start))
                continue

            invalid_bracket = _consume_invalid_bracket(state)
            raise InvalidBracketError(
                invalid_bracket,
                span=SourceSpan(start=start, end=state.mark()),
            )

        if _is_label_or_type_char(char):
            while _can_continue_label_or_type(state):
                state.advance()
            tokens.append(state.emit(QueryTokenKind.identifier, start))
            continue

        state.advance()
        raise QuerySyntaxError(
            f"Unexpected character '{char}' in query.",
            span=SourceSpan(start=start, end=state.mark()),
        )

    return tuple(tokens)


def _consume_preview_modifier(state: _TokenizerState) -> bool:
    checkpoint = (state.offset, state.line, state.column)

    if state.advance() != "[":
        return False
    if state.is_at_end() or state.current() != "p":
        _restore_state(state, checkpoint)
        return False

    state.advance()
    digit_count = 0
    while not state.is_at_end() and state.current().isdigit():
        digit_count += 1
        state.advance()

    if digit_count == 0 or state.is_at_end() or state.current() != "]":
        _restore_state(state, checkpoint)
        return False

    state.advance()
    return True


def _consume_invalid_scope(state: _TokenizerState) -> str:
    start_offset = state.offset
    state.advance()
    while (
        not state.is_at_end()
        and not _is_whitespace(state.current())
        and state.current() not in "%@*["
    ):
        state.advance()
    return state.query_text[start_offset : state.offset]


def _consume_invalid_bracket(state: _TokenizerState) -> str:
    start_offset = state.offset
    state.advance()
    while not state.is_at_end() and not _is_whitespace(state.current()):
        char = state.advance()
        if char == "]":
            break
    return state.query_text[start_offset : state.offset]


def _restore_state(state: _TokenizerState, checkpoint: tuple[int, int, int]) -> None:
    state.offset, state.line, state.column = checkpoint


def _matches_exact_scope_token(state: _TokenizerState, token_text: str) -> bool:
    if not state.startswith(token_text):
        return False

    next_offset = state.offset + len(token_text)
    if next_offset >= len(state.query_text):
        return True

    return not _is_label_or_type_char(state.query_text[next_offset])


def _is_label_or_type_char(char: str) -> bool:
    return char.isalnum() or char in ":_.-"


def _can_continue_label_or_type(state: _TokenizerState) -> bool:
    return (
        not state.is_at_end()
        and _is_label_or_type_char(state.current())
        and not state.startswith("..")
    )


def _is_whitespace(char: str) -> bool:
    return char in " \t\n\r"
