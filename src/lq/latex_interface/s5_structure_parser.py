from pathlib import Path

from lq.latex_interface.data_model import (
    LatexBlock,
    LatexDocument,
    LatexLabel,
    validate_all_latex_labels,
    validate_latex_label_content,
)
from lq.latex_interface.input_resolver import resolve_latex_includes
from lq.latex_interface.s1_source import (
    LatexSourcePosition,
    LatexSourceSpan,
    LatexSourceText,
    slice_latex_source,
)
from lq.latex_interface.s2_scan_model import LatexToken, LatexTokenKind
from lq.latex_interface.s3_scanner import scan_latex
from lq.latex_interface.s4_structure_model import (
    LatexStructuralBlock,
    LatexStructuralBlockKind,
    LatexStructuralCommand,
    LatexStructuralCommandKind,
    LatexStructuralDocument,
)
from lq.latex_interface.s6_content_helpers import collect_labels
from lq.utils.io import FileReader


def parse_latex_structure(input_latex: LatexSourceText) -> LatexStructuralDocument:
    tokens = scan_latex(input_latex)
    all_discovered_labels = list(collect_labels(input_latex))
    validate_all_latex_labels(all_discovered_labels)
    all_source_labels = frozenset(all_discovered_labels)

    commands = _collect_structural_commands(tokens, input_latex)
    begin_document = _find_first_command(
        commands,
        LatexStructuralCommandKind.begin_document,
    )
    if begin_document is None:
        raise Exception(r"parse_latex: \begin{document} not found.")

    end_document = _find_last_command(
        commands,
        LatexStructuralCommandKind.end_document,
    )
    if end_document is None:
        raise Exception(r"parse_latex: \end{document} not found.")

    pre_matter_span = _build_span(
        _start_of_file(),
        begin_document.span.start,
    )
    if not slice_latex_source(input_latex, pre_matter_span).startswith(
        r"\documentclass"
    ):
        raise Exception(r"parse_latex: \documentclass expected to be at start of file.")

    maketitle_commands = _find_commands(commands, LatexStructuralCommandKind.maketitle)
    if not maketitle_commands:
        raise Exception(r"parse_latex: \maketitle not found.")
    if len(maketitle_commands) > 1:
        raise Exception(r"parse_latex: at most one \maketitle is supported.")
    assert len(maketitle_commands) == 1
    maketitle = maketitle_commands[0]

    begin_document_span = _build_span(begin_document.span.end, maketitle.span.start)

    bibliography = _find_first_command_after(
        commands,
        LatexStructuralCommandKind.bibliography,
        maketitle.span.end.offset,
    )
    content_end = (
        bibliography.span.start.offset
        if bibliography is not None
        else end_document.span.start.offset
    )
    bibliography_start = (
        bibliography.span.start if bibliography is not None else end_document.span.start
    )
    bibliography_span = _build_span(bibliography_start, end_document.span.start)
    post_document_span = _build_span(
        end_document.span.end,
        _end_of_input(input_latex),
    )

    appendix = _find_first_command_in_range(
        commands,
        LatexStructuralCommandKind.appendix,
        maketitle.span.end.offset,
        content_end,
    )

    main_blocks = _parse_part_blocks(
        commands=commands,
        tokens=tokens,
        input_latex=input_latex,
        start_offset=maketitle.span.end.offset,
        end_offset=appendix.span.start.offset if appendix is not None else content_end,
        in_appendix=False,
    )

    appendix_blocks: tuple[LatexStructuralBlock, ...]
    if appendix is None:
        appendix_blocks = ()
    else:
        appendix_blocks = _parse_part_blocks(
            commands=commands,
            tokens=tokens,
            input_latex=input_latex,
            start_offset=appendix.span.end.offset,
            end_offset=content_end,
            in_appendix=True,
        )

    return LatexStructuralDocument(
        pre_matter_span=pre_matter_span,
        begin_document_span=begin_document_span,
        blocks=main_blocks + appendix_blocks,
        bibliography_span=bibliography_span,
        post_document_span=post_document_span,
        all_source_labels=all_source_labels,
        commands=commands,
    )


def parse_from_latex_with_structure_parser(
    input_latex: str,
    supporting_files: dict[Path, bytes] | None = None,
) -> LatexDocument:
    structure = parse_latex_structure(input_latex)
    blocks: list[LatexBlock] = []

    for block in structure.blocks:
        if block.kind is LatexStructuralBlockKind.pre_section:
            blocks.append(
                LatexBlock.pre_section(
                    in_appendix=block.in_appendix,
                    content=slice_latex_source(input_latex, block.content_span),
                )
            )
            continue

        assert block.heading_span is not None
        content = slice_latex_source(
            input_latex,
            _build_span(block.heading_span.start, block.content_span.end),
        )
        if block.kind is LatexStructuralBlockKind.section:
            blocks.append(
                LatexBlock.section(
                    in_appendix=block.in_appendix,
                    content=content,
                    all_labels=block.all_labels,
                )
            )
            continue

        blocks.append(
            LatexBlock.subsection(
                in_appendix=block.in_appendix,
                content=content,
                all_labels=block.all_labels,
            )
        )

    return LatexDocument(
        pre_matter=slice_latex_source(input_latex, structure.pre_matter_span),
        begin_document=slice_latex_source(input_latex, structure.begin_document_span),
        blocks=tuple(blocks),
        all_source_labels=structure.all_source_labels,
        bibliography=slice_latex_source(input_latex, structure.bibliography_span),
        post_document=slice_latex_source(input_latex, structure.post_document_span),
        supporting_files=supporting_files or {},
    )


def parse_latex_from_files_with_structure_parser(
    file_reader: FileReader,
    main_file: Path,
    supporting_file_paths: list[Path],
    supporting_files: dict[Path, bytes] | None = None,
) -> LatexDocument:
    resolved_content = resolve_latex_includes(
        file_reader,
        main_file,
        supporting_file_paths=supporting_file_paths,
    ).expanded_latex
    return parse_from_latex_with_structure_parser(
        resolved_content,
        supporting_files=supporting_files,
    )


def _parse_part_blocks(
    *,
    commands: tuple[LatexStructuralCommand, ...],
    tokens: tuple[LatexToken, ...],
    input_latex: LatexSourceText,
    start_offset: int,
    end_offset: int,
    in_appendix: bool,
) -> tuple[LatexStructuralBlock, ...]:
    section_commands = _find_commands_in_range(
        commands,
        start_offset,
        end_offset,
        kinds={
            LatexStructuralCommandKind.section,
            LatexStructuralCommandKind.subsection,
        },
    )

    if (
        section_commands
        and section_commands[0].kind is LatexStructuralCommandKind.subsection
    ):
        part_name = "appendix" if in_appendix else "main body"
        raise ValueError(
            "Unsupported document structure: "
            f"{part_name} must begin with \\section{{...}}, not \\subsection{{...}}."
        )

    first_section_start = (
        section_commands[0].span.start
        if section_commands
        else _position_at_offset(tokens, end_offset)
    )
    blocks: list[LatexStructuralBlock] = [
        LatexStructuralBlock(
            kind=LatexStructuralBlockKind.pre_section,
            in_appendix=in_appendix,
            heading_span=None,
            content_span=_build_span(
                _position_at_offset(tokens, start_offset),
                first_section_start,
            ),
            title=None,
            label=None,
            all_labels=frozenset(),
        )
    ]

    top_level_sections = [
        command
        for command in section_commands
        if command.kind is LatexStructuralCommandKind.section
    ]

    for index, section in enumerate(top_level_sections):
        section_end_offset = (
            top_level_sections[index + 1].span.start.offset
            if index + 1 < len(top_level_sections)
            else end_offset
        )
        subsection_commands = [
            command
            for command in section_commands
            if command.kind is LatexStructuralCommandKind.subsection
            and section.span.end.offset
            <= command.span.start.offset
            < section_end_offset
        ]

        first_subsection_start = (
            subsection_commands[0].span.start
            if subsection_commands
            else _position_at_offset(tokens, section_end_offset)
        )
        blocks.append(
            LatexStructuralBlock(
                kind=LatexStructuralBlockKind.section,
                in_appendix=in_appendix,
                heading_span=section.span,
                content_span=_build_span(section.span.end, first_subsection_start),
                title=section.title,
                label=_find_direct_label_in_range(
                    tokens,
                    input_latex,
                    section.span.end.offset,
                    first_subsection_start.offset,
                ),
                all_labels=frozenset(
                    _collect_labels_in_range(
                        input_latex,
                        section.span.end.offset,
                        section_end_offset,
                    )
                ),
            )
        )

        for subsection_index, subsection in enumerate(subsection_commands):
            subsection_end_offset = (
                subsection_commands[subsection_index + 1].span.start.offset
                if subsection_index + 1 < len(subsection_commands)
                else section_end_offset
            )
            subsection_end = _position_at_offset(tokens, subsection_end_offset)
            blocks.append(
                LatexStructuralBlock(
                    kind=LatexStructuralBlockKind.subsection,
                    in_appendix=in_appendix,
                    heading_span=subsection.span,
                    content_span=_build_span(subsection.span.end, subsection_end),
                    title=subsection.title,
                    label=_find_direct_label_in_range(
                        tokens,
                        input_latex,
                        subsection.span.end.offset,
                        subsection_end_offset,
                    ),
                    all_labels=frozenset(
                        _collect_labels_in_range(
                            input_latex,
                            subsection.span.end.offset,
                            subsection_end_offset,
                        )
                    ),
                )
            )

    return tuple(blocks)


def _find_commands_in_range(
    commands: tuple[LatexStructuralCommand, ...],
    start_offset: int,
    end_offset: int,
    *,
    kinds: set[LatexStructuralCommandKind],
) -> tuple[LatexStructuralCommand, ...]:
    return tuple(
        command
        for command in commands
        if command.kind in kinds
        and start_offset <= command.span.start.offset < end_offset
    )


def _find_commands(
    commands: tuple[LatexStructuralCommand, ...],
    kind: LatexStructuralCommandKind,
) -> tuple[LatexStructuralCommand, ...]:
    return tuple(command for command in commands if command.kind is kind)


def _collect_structural_commands(
    tokens: tuple[LatexToken, ...],
    input_latex: LatexSourceText,
) -> tuple[LatexStructuralCommand, ...]:
    commands: list[LatexStructuralCommand] = []
    in_document = False
    nested_environment_depth = 0

    for token in tokens:
        if token.kind is LatexTokenKind.begin_environment:
            if not in_document:
                if token.name == "document":
                    commands.append(
                        LatexStructuralCommand(
                            kind=LatexStructuralCommandKind.begin_document,
                            span=_token_full_span(token),
                            title=None,
                        )
                    )
                    in_document = True
                continue

            if nested_environment_depth == 0 and token.name == "thebibliography":
                commands.append(
                    LatexStructuralCommand(
                        kind=LatexStructuralCommandKind.bibliography,
                        span=_token_full_span(token),
                        title=None,
                    )
                )
            nested_environment_depth += 1
            continue

        if token.kind is LatexTokenKind.end_environment:
            if (
                in_document
                and nested_environment_depth == 0
                and token.name == "document"
            ):
                commands.append(
                    LatexStructuralCommand(
                        kind=LatexStructuralCommandKind.end_document,
                        span=_token_full_span(token),
                        title=None,
                    )
                )
                in_document = False
                continue

            if in_document and nested_environment_depth > 0:
                nested_environment_depth -= 1
            continue

        if not in_document or nested_environment_depth != 0:
            continue

        if token.kind is not LatexTokenKind.command or token.name is None:
            continue

        if token.name == "maketitle":
            commands.append(
                LatexStructuralCommand(
                    kind=LatexStructuralCommandKind.maketitle,
                    span=_token_full_span(token),
                    title=None,
                )
            )
            continue

        if token.name == "appendix":
            commands.append(
                LatexStructuralCommand(
                    kind=LatexStructuralCommandKind.appendix,
                    span=_token_full_span(token),
                    title=None,
                )
            )
            continue

        if token.name == "bibliography":
            commands.append(
                LatexStructuralCommand(
                    kind=LatexStructuralCommandKind.bibliography,
                    span=_token_full_span(token),
                    title=None,
                )
            )
            continue

        if token.name not in {"section", "subsection"}:
            continue

        title = _get_required_group_content(token, input_latex)
        if title is None:
            continue

        commands.append(
            LatexStructuralCommand(
                kind=(
                    LatexStructuralCommandKind.section
                    if token.name == "section"
                    else LatexStructuralCommandKind.subsection
                ),
                span=_token_full_span(token),
                title=title,
            )
        )

    return tuple(commands)


def _find_direct_label_in_range(
    tokens: tuple[LatexToken, ...],
    input_latex: LatexSourceText,
    start_offset: int,
    end_offset: int,
) -> LatexLabel | None:
    nested_environment_depth = 0

    for token in tokens:
        if token.span.start.offset < start_offset:
            continue
        if token.span.start.offset >= end_offset:
            break

        if token.kind is LatexTokenKind.begin_environment:
            if nested_environment_depth == 0:
                return None
            nested_environment_depth += 1
            continue

        if token.kind is LatexTokenKind.end_environment:
            if nested_environment_depth > 0:
                nested_environment_depth -= 1
            continue

        if nested_environment_depth != 0:
            continue

        if token.kind in {LatexTokenKind.text, LatexTokenKind.comment}:
            continue

        if token.kind is LatexTokenKind.command and token.name == "label":
            return _get_required_group_content(token, input_latex)

        return None

    return None


def _collect_labels_in_range(
    input_latex: LatexSourceText,
    start_offset: int,
    end_offset: int | None,
) -> list[LatexLabel]:
    return list(collect_labels(input_latex[start_offset:end_offset]))


def _get_required_group_content(
    token: LatexToken,
    input_latex: LatexSourceText,
) -> str | None:
    for argument_span in token.argument_spans:
        argument_text = slice_latex_source(input_latex, argument_span)
        if argument_text.startswith("{") and argument_text.endswith("}"):
            content = argument_text[1:-1]
            if token.name == "label":
                validate_latex_label_content(content)
            return content
    return None


def _token_full_span(token: LatexToken) -> LatexSourceSpan:
    if not token.argument_spans:
        return token.span
    return LatexSourceSpan(start=token.span.start, end=token.argument_spans[-1].end)


def _build_span(
    start: LatexSourcePosition,
    end: LatexSourcePosition,
) -> LatexSourceSpan:
    return LatexSourceSpan(start=start, end=end)


def _start_of_file() -> LatexSourcePosition:
    return LatexSourcePosition(offset=0, line=1, column=1)


def _end_of_input(input_latex: LatexSourceText) -> LatexSourcePosition:
    line = 1
    column = 1
    for character in input_latex:
        if character == "\n":
            line += 1
            column = 1
            continue
        column += 1

    return LatexSourcePosition(offset=len(input_latex), line=line, column=column)


def _position_at_offset(
    tokens: tuple[LatexToken, ...],
    offset: int,
) -> LatexSourcePosition:
    if offset == 0:
        return _start_of_file()

    for token in tokens:
        if token.span.start.offset == offset:
            return token.span.start
        if token.span.end.offset == offset:
            return token.span.end
        for argument_span in token.argument_spans:
            if argument_span.start.offset == offset:
                return argument_span.start
            if argument_span.end.offset == offset:
                return argument_span.end

    if not tokens:
        return _start_of_file()

    last_token = tokens[-1]
    if last_token.span.end.offset == offset:
        return last_token.span.end

    raise ValueError(f"No source position found for offset {offset}.")


def _find_first_command(
    commands: tuple[LatexStructuralCommand, ...],
    kind: LatexStructuralCommandKind,
) -> LatexStructuralCommand | None:
    for command in commands:
        if command.kind is kind:
            return command
    return None


def _find_last_command(
    commands: tuple[LatexStructuralCommand, ...],
    kind: LatexStructuralCommandKind,
) -> LatexStructuralCommand | None:
    for command in reversed(commands):
        if command.kind is kind:
            return command
    return None


def _find_first_command_after(
    commands: tuple[LatexStructuralCommand, ...],
    kind: LatexStructuralCommandKind,
    offset: int,
) -> LatexStructuralCommand | None:
    for command in commands:
        if command.kind is kind and command.span.start.offset >= offset:
            return command
    return None


def _find_first_command_in_range(
    commands: tuple[LatexStructuralCommand, ...],
    kind: LatexStructuralCommandKind,
    start_offset: int,
    end_offset: int,
) -> LatexStructuralCommand | None:
    for command in commands:
        if command.kind is not kind:
            continue
        if start_offset <= command.span.start.offset < end_offset:
            return command
    return None
