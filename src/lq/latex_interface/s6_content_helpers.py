from collections.abc import Container, Iterator

from lq.latex_interface.data_model import (
    LatexContent,
    LatexLabel,
    validate_latex_label_content,
)
from lq.latex_interface.s1_source import slice_latex_source
from lq.latex_interface.s2_scan_model import LatexToken, LatexTokenKind
from lq.latex_interface.s3_scanner import scan_latex


def collect_labels(content: LatexContent) -> tuple[LatexLabel, ...]:
    return tuple(_iter_labels(content))


def content_has_any_label(content: LatexContent) -> bool:
    return any(_iter_labels(content))


def split_leading_label_command(
    content: LatexContent,
) -> tuple[LatexContent, LatexContent]:
    for token in scan_latex(content):
        if token.kind is LatexTokenKind.text and token.text.strip() == "":
            continue

        if token.kind is LatexTokenKind.command and token.name == "label":
            label_end_offset = _token_end_offset(token)
            if content[label_end_offset:].startswith("\n"):
                label_end_offset += 1

            return content[:label_end_offset], content[label_end_offset:]

        return "", content

    return "", content


def _iter_required_group_arguments_in_text(
    content: LatexContent,
    command_names: Container[str],
) -> Iterator[tuple[LatexContent, ...]]:
    tokens = scan_latex(content)
    index = 0

    while index < len(tokens):
        token = tokens[index]
        covered_until = None

        if token.kind in {
            LatexTokenKind.command,
            LatexTokenKind.begin_environment,
            LatexTokenKind.end_environment,
        }:
            if token.name in command_names:
                yield tuple(
                    argument_text[1:-1]
                    for argument_span in token.argument_spans
                    for argument_text in [slice_latex_source(content, argument_span)]
                    if argument_text.startswith("{") and argument_text.endswith("}")
                )

            for argument_span in token.argument_spans:
                group_text = slice_latex_source(content, argument_span)
                if len(group_text) >= 2:
                    yield from _iter_required_group_arguments_in_text(
                        group_text[1:-1],
                        command_names,
                    )

            covered_until = _token_end_offset(token)
        elif token.kind in {LatexTokenKind.group, LatexTokenKind.optional_group}:
            group_text = slice_latex_source(content, token.span)
            if len(group_text) >= 2:
                yield from _iter_required_group_arguments_in_text(
                    group_text[1:-1],
                    command_names,
                )
            covered_until = token.span.end.offset

        index += 1
        if covered_until is None:
            continue

        while index < len(tokens) and tokens[index].span.start.offset < covered_until:
            index += 1


def _iter_labels(content: LatexContent) -> Iterator[LatexLabel]:
    for arguments in _iter_required_group_arguments_in_text(content, {"label"}):
        for argument in arguments:
            stripped_argument = argument.strip()
            if stripped_argument != "":
                validate_latex_label_content(stripped_argument)
                yield stripped_argument
                break


def _token_end_offset(token: LatexToken) -> int:
    if not token.argument_spans:
        return token.span.end.offset

    return token.argument_spans[-1].end.offset
