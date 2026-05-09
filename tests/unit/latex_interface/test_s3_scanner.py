from lq.latex_interface.s1_source import LatexSourcePosition, LatexSourceSpan
from lq.latex_interface.s2_scan_model import LatexToken, LatexTokenKind
from lq.latex_interface.s3_scanner import scan_latex


def test_scan_preserves_text_comment_and_positions():
    input_latex = "A% note\nB"

    assert scan_latex(input_latex) == (
        LatexToken(
            kind=LatexTokenKind.text,
            text="A",
            span=LatexSourceSpan(
                start=LatexSourcePosition(offset=0, line=1, column=1),
                end=LatexSourcePosition(offset=1, line=1, column=2),
            ),
            name=None,
            argument_spans=(),
        ),
        LatexToken(
            kind=LatexTokenKind.comment,
            text="% note\n",
            span=LatexSourceSpan(
                start=LatexSourcePosition(offset=1, line=1, column=2),
                end=LatexSourcePosition(offset=8, line=2, column=1),
            ),
            name=None,
            argument_spans=(),
        ),
        LatexToken(
            kind=LatexTokenKind.text,
            text="B",
            span=LatexSourceSpan(
                start=LatexSourcePosition(offset=8, line=2, column=1),
                end=LatexSourcePosition(offset=9, line=2, column=2),
            ),
            name=None,
            argument_spans=(),
        ),
    )


def test_scan_records_command_argument_spans_and_group_tokens():
    input_latex = r"\section[short]{Long title}"

    assert scan_latex(input_latex) == (
        LatexToken(
            kind=LatexTokenKind.command,
            text=r"\section",
            span=LatexSourceSpan(
                start=LatexSourcePosition(offset=0, line=1, column=1),
                end=LatexSourcePosition(offset=8, line=1, column=9),
            ),
            name="section",
            argument_spans=(
                LatexSourceSpan(
                    start=LatexSourcePosition(offset=8, line=1, column=9),
                    end=LatexSourcePosition(offset=15, line=1, column=16),
                ),
                LatexSourceSpan(
                    start=LatexSourcePosition(offset=15, line=1, column=16),
                    end=LatexSourcePosition(offset=27, line=1, column=28),
                ),
            ),
        ),
        LatexToken(
            kind=LatexTokenKind.optional_group,
            text="[short]",
            span=LatexSourceSpan(
                start=LatexSourcePosition(offset=8, line=1, column=9),
                end=LatexSourcePosition(offset=15, line=1, column=16),
            ),
            name=None,
            argument_spans=(),
        ),
        LatexToken(
            kind=LatexTokenKind.group,
            text="{Long title}",
            span=LatexSourceSpan(
                start=LatexSourcePosition(offset=15, line=1, column=16),
                end=LatexSourcePosition(offset=27, line=1, column=28),
            ),
            name=None,
            argument_spans=(),
        ),
    )


def test_scan_recognizes_begin_and_end_environment_tokens():
    input_latex = r"\begin{proof}\label{sec:proof}\end{proof}"

    assert [token.kind for token in scan_latex(input_latex)] == [
        LatexTokenKind.begin_environment,
        LatexTokenKind.group,
        LatexTokenKind.command,
        LatexTokenKind.group,
        LatexTokenKind.end_environment,
        LatexTokenKind.group,
    ]

    begin_token, _, label_token, _, end_token, _ = scan_latex(input_latex)
    assert begin_token.name == "proof"
    assert label_token.name == "label"
    assert end_token.name == "proof"


def test_scan_ignores_escaped_percent_and_escaped_braces_inside_group():
    input_latex = r"\label{sec:50\%\{ok\}} % trailing comment"

    tokens = scan_latex(input_latex)

    assert tokens[0] == LatexToken(
        kind=LatexTokenKind.command,
        text=r"\label",
        span=LatexSourceSpan(
            start=LatexSourcePosition(offset=0, line=1, column=1),
            end=LatexSourcePosition(offset=6, line=1, column=7),
        ),
        name="label",
        argument_spans=(
            LatexSourceSpan(
                start=LatexSourcePosition(offset=6, line=1, column=7),
                end=LatexSourcePosition(offset=22, line=1, column=23),
            ),
        ),
    )
    assert tokens[1].kind is LatexTokenKind.group
    assert tokens[1].text == r"{sec:50\%\{ok\}}"
    assert tokens[2].kind is LatexTokenKind.text
    assert tokens[2].text == " "
    assert tokens[3].kind is LatexTokenKind.comment


def test_scan_fails_for_unterminated_group():
    input_latex = r"\section{Missing end"

    try:
        scan_latex(input_latex)
    except ValueError as exc:
        assert str(exc) == "Unterminated {} group starting at line 1, column 9."
    else:
        raise AssertionError("Expected ValueError for unterminated group")


def test_scan_treats_unmatched_open_bracket_as_text():
    input_latex = "Text [i"

    assert scan_latex(input_latex) == (
        LatexToken(
            kind=LatexTokenKind.text,
            text="Text [i",
            span=LatexSourceSpan(
                start=LatexSourcePosition(offset=0, line=1, column=1),
                end=LatexSourcePosition(offset=7, line=1, column=8),
            ),
            name=None,
            argument_spans=(),
        ),
    )
