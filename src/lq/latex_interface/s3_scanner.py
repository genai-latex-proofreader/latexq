from dataclasses import dataclass

from lq.latex_interface.s1_source import (
    LatexSourcePosition,
    LatexSourceSpan,
    LatexSourceText,
    slice_latex_source,
)
from lq.latex_interface.s2_scan_model import LatexToken, LatexTokenKind


@dataclass
class _ScannerState:
    text: LatexSourceText
    offset: int = 0
    line: int = 1
    column: int = 1

    def clone(self) -> "_ScannerState":
        return _ScannerState(
            text=self.text,
            offset=self.offset,
            line=self.line,
            column=self.column,
        )

    def is_at_end(self) -> bool:
        return self.offset >= len(self.text)

    def current(self) -> str:
        return self.text[self.offset]

    def mark(self) -> LatexSourcePosition:
        return LatexSourcePosition(
            offset=self.offset,
            line=self.line,
            column=self.column,
        )

    def advance(self) -> str:
        char = self.text[self.offset]
        self.offset += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def emit(
        self,
        kind: LatexTokenKind,
        start: LatexSourcePosition,
        *,
        name: str | None,
        argument_spans: tuple[LatexSourceSpan, ...],
    ) -> LatexToken:
        end = self.mark()
        span = LatexSourceSpan(start=start, end=end)
        return LatexToken(
            kind=kind,
            text=slice_latex_source(self.text, span),
            span=span,
            name=name,
            argument_spans=argument_spans,
        )


def scan_latex(text: LatexSourceText) -> tuple[LatexToken, ...]:
    """Tokenize LaTeX source into low-level scanner tokens."""
    state = _ScannerState(text=text)
    tokens: list[LatexToken] = []

    while not state.is_at_end():
        char = state.current()

        if char == "%":
            tokens.append(_scan_comment(state))
            continue

        if char == "\\":
            tokens.append(_scan_command(state))
            continue

        if char == "{":
            tokens.append(_scan_group_token(state, "{", "}", LatexTokenKind.group))
            continue

        if char == "[":
            tokens.append(_scan_optional_group_or_text(state))
            continue

        tokens.append(_scan_text(state))

    return tuple(tokens)


def _scan_text(
    state: _ScannerState,
    stop_chars: str = "\\%[{",
) -> LatexToken:
    start = state.mark()

    while not state.is_at_end():
        current = state.current()

        if current in stop_chars.replace("[", ""):
            break

        if current == "[":
            lookahead = state.clone()
            try:
                _consume_group_span(lookahead, "[", "]")
            except ValueError:
                state.advance()
                continue

            if "[" in stop_chars:
                break

        state.advance()

    return state.emit(
        LatexTokenKind.text,
        start,
        name=None,
        argument_spans=(),
    )


def _scan_comment(state: _ScannerState) -> LatexToken:
    start = state.mark()
    state.advance()

    while not state.is_at_end() and state.current() != "\n":
        state.advance()

    if not state.is_at_end() and state.current() == "\n":
        state.advance()

    return state.emit(
        LatexTokenKind.comment,
        start,
        name=None,
        argument_spans=(),
    )


def _scan_command(state: _ScannerState) -> LatexToken:
    start = state.mark()
    state.advance()

    if state.is_at_end():
        return state.emit(
            LatexTokenKind.command,
            start,
            name="",
            argument_spans=(),
        )

    if state.current().isalpha():
        name = _advance_letters(state)
    else:
        name = state.advance()

    argument_spans = _peek_argument_spans(state)
    token_kind = LatexTokenKind.command
    token_name: str | None = name

    if name in {"begin", "end"}:
        environment_name = _extract_environment_name(state.text, argument_spans)
        if environment_name is not None:
            token_kind = (
                LatexTokenKind.begin_environment
                if name == "begin"
                else LatexTokenKind.end_environment
            )
            token_name = environment_name

    return state.emit(
        token_kind,
        start,
        name=token_name,
        argument_spans=argument_spans,
    )


def _advance_letters(state: _ScannerState) -> str:
    letters: list[str] = []
    while not state.is_at_end() and state.current().isalpha():
        letters.append(state.advance())
    return "".join(letters)


def _peek_argument_spans(state: _ScannerState) -> tuple[LatexSourceSpan, ...]:
    lookahead = state.clone()
    argument_spans: list[LatexSourceSpan] = []

    while True:
        _consume_whitespace(lookahead)

        if lookahead.is_at_end():
            return tuple(argument_spans)

        if lookahead.current() == "{":
            argument_spans.append(_consume_group_span(lookahead, "{", "}"))
            continue

        if lookahead.current() == "[":
            argument_spans.append(_consume_group_span(lookahead, "[", "]"))
            continue

        return tuple(argument_spans)


def _consume_whitespace(state: _ScannerState) -> None:
    while not state.is_at_end() and state.current() in " \t\n\r":
        state.advance()


def _scan_group_token(
    state: _ScannerState,
    open_char: str,
    close_char: str,
    kind: LatexTokenKind,
) -> LatexToken:
    start = state.mark()
    _consume_group_span(state, open_char, close_char)
    return state.emit(kind, start, name=None, argument_spans=())


def _scan_optional_group_or_text(state: _ScannerState) -> LatexToken:
    lookahead = state.clone()

    try:
        _consume_group_span(lookahead, "[", "]")
    except ValueError:
        return _scan_text(state, stop_chars="\\%{")

    return _scan_group_token(state, "[", "]", LatexTokenKind.optional_group)


def _consume_group_span(
    state: _ScannerState,
    open_char: str,
    close_char: str,
) -> LatexSourceSpan:
    start = state.mark()
    depth = 0

    while not state.is_at_end():
        char = state.advance()

        if char == "\\":
            if not state.is_at_end():
                state.advance()
            continue

        if char == "%":
            while not state.is_at_end() and state.current() != "\n":
                state.advance()
            continue

        if char == open_char:
            depth += 1
            continue

        if char == close_char:
            depth -= 1
            if depth == 0:
                return LatexSourceSpan(start=start, end=state.mark())

    raise ValueError(
        f"Unterminated {open_char}{close_char} group starting at line {start.line}, column {start.column}."
    )


def _extract_environment_name(
    text: LatexSourceText,
    argument_spans: tuple[LatexSourceSpan, ...],
) -> str | None:
    if not argument_spans:
        return None

    first_argument = slice_latex_source(text, argument_spans[0])
    if not first_argument.startswith("{") or not first_argument.endswith("}"):
        return None

    return first_argument[1:-1]
