import fnmatch
from pathlib import Path

from lq.config import load_config
from lq.latex_interface.data_model import (
    LatexBlock,
    LatexBlockKind,
    LatexContent,
    LatexDocument,
    render_latex_document,
)
from lq.latex_interface.input_resolver import resolve_latex_includes
from lq.latex_interface.parser import parse_latex_from_files
from lq.latex_interface.roundtrip import validate_latex_roundtrip
from lq.split.data_model import Granularity, SplitConfig
from lq.utils.io import DirectoryFileReader, write_directory


def _append_input_command(inputs: list[LatexContent], rel_path: Path) -> None:
    r"""Append a generated ``\input{...}`` command on its own line."""
    if not inputs or not inputs[-1].endswith("\n"):
        inputs.append("\n")
    inputs.append(f"\\input{{{rel_path}}}\n")


def _get_section_filename(
    block: LatexBlock,
    section_counter: int,
    granularity: Granularity,
    prefix: str = "s",
) -> str:
    """Get the numbered filename for a section.

    Args:
        block: The section block.
        section_counter: The counter for this section type.
        granularity: Split granularity for filename format.
        prefix: File prefix ('s' for main sections, 'a' for appendix sections).
    """
    subsection_slot = ""
    if granularity is Granularity.subsection:
        subsection_slot = "_00"

    if block.label:
        normalized = block.label.lower().replace(":", "_")
        return f"{prefix}{section_counter:02d}{subsection_slot}_{normalized}.tex"

    return f"{prefix}{section_counter:02d}{subsection_slot}.tex"


def _get_subsection_filename(
    block: LatexBlock,
    section_counter: int,
    subsection_counter: int,
    prefix: str = "s",
) -> str:
    """Get the numbered filename for a subsection within a section.

    Args:
        block: The subsection block.
        section_counter: The counter for this section type.
        subsection_counter: The counter for this subsection.
        prefix: File prefix ('s' for main sections, 'a' for appendix sections).
    """
    if block.label:
        normalized = block.label.lower().replace(":", "_")
        return (
            f"{prefix}{section_counter:02d}_{subsection_counter:02d}_{normalized}.tex"
        )

    return f"{prefix}{section_counter:02d}_{subsection_counter:02d}.tex"


def _process_blocks(
    blocks: tuple[LatexBlock, ...],
    granularity: Granularity,
    sections_dir: str,
    prefix: str = "s",
) -> tuple[list[LatexContent], dict[Path, LatexContent]]:
    """Process ordered blocks (main or appendix) into inputs and section files.

    Args:
        blocks: The filtered blocks to process.
        sections_dir: Directory name for section files.
        prefix: File prefix ('s' for main sections, 'a' for appendix sections).

    Returns:
        Tuple of (input_lines, section_files)
    """
    inputs: list[LatexContent] = []
    section_files: dict[Path, LatexContent] = {}
    section_counter = 0
    current_section_counter = 0
    current_section_path: Path | None = None
    subsection_counter = 0

    for block in blocks:
        if block.kind is LatexBlockKind.pre_section:
            inputs.append(block.content)
        elif block.kind is LatexBlockKind.subsection:
            if granularity == Granularity.section and current_section_path is not None:
                section_files[current_section_path] += block.content
                continue

            if current_section_counter == 0:
                raise ValueError(
                    "Unsupported document structure: subsection encountered before any section."
                )

            subsection_counter += 1
            filename = _get_subsection_filename(
                block,
                current_section_counter,
                subsection_counter,
                prefix=prefix,
            )
            rel_path = Path(sections_dir) / filename

            section_files[rel_path] = block.content
            _append_input_command(inputs, rel_path)
        else:
            section_counter += 1
            current_section_counter = section_counter
            subsection_counter = 0
            filename = _get_section_filename(
                block,
                section_counter,
                granularity,
                prefix=prefix,
            )
            rel_path = Path(sections_dir) / filename

            section_files[rel_path] = block.content
            current_section_path = rel_path
            _append_input_command(inputs, rel_path)

    return inputs, section_files


def _split_document(
    doc: LatexDocument, config: SplitConfig
) -> tuple[LatexContent, dict[Path, LatexContent]]:
    """Split document into a main file and generated section files.

    Returns:
        Tuple of (main_file_content, {relative_path: file_content})
    """
    # Process main content
    main_blocks = doc.main_blocks()
    main_inputs, main_files = _process_blocks(
        main_blocks,
        config.granularity,
        config.main_sections_dir,
        prefix="s",
    )

    # Process appendix content (with separate numbering starting from 01)
    appendix_blocks = doc.appendix_blocks()
    appendix_inputs, appendix_files = _process_blocks(
        appendix_blocks,
        config.granularity,
        config.appendix_sections_dir,
        prefix="a",
    )

    # Merge section files
    all_section_files = {**main_files, **appendix_files}

    main_inputs_str = "".join(main_inputs)
    appendix_inputs_str = "".join(appendix_inputs)

    appendix = None
    if appendix_blocks:
        appendix = appendix_inputs_str

    return (
        render_latex_document(
            pre_matter=doc.pre_matter,
            begin_document=doc.begin_document,
            main_body=main_inputs_str,
            appendix=appendix,
            bibliography=doc.bibliography,
            post_document=doc.post_document,
        ),
        all_section_files,
    )


def _get_supporting_file_paths(
    file_paths: tuple[Path, ...],
    config: SplitConfig,
) -> list[Path]:
    return [
        file_path
        for file_path in file_paths
        if any(fnmatch.fnmatch(str(file_path), pat) for pat in config.supporting_files)
    ]


def _validate_input_manuscript_roundtrip(
    input_file: Path,
    config_file: Path,
) -> None:
    split_config = load_config(config_file).split
    input_path = input_file.resolve()
    file_reader = DirectoryFileReader(input_path.parent)
    supporting_file_paths = _get_supporting_file_paths(
        file_reader.list_paths(),
        split_config,
    )

    resolved_inputs = resolve_latex_includes(
        file_reader,
        Path(input_path.name),
        supporting_file_paths=supporting_file_paths,
    )
    validate_latex_roundtrip(resolved_inputs.expanded_latex)


def _generate_split_output(
    input_file: Path,
    config_file: Path,
) -> tuple[Path, SplitConfig, dict[Path, bytes | str]]:
    config = load_config(config_file)

    input_path = input_file.resolve()
    file_reader = DirectoryFileReader(input_path.parent)

    # Supporting files:
    #  - will be copied to output directory (eg style files, images)
    #  - \include:s referencing supporting files are not expanded. These can eg be used
    #    for programmatically generated tables or a macro definition file.
    supporting_file_paths = _get_supporting_file_paths(
        file_reader.list_paths(),
        config.split,
    )
    supporting_files = {
        path: file_reader.read_bytes(path) for path in supporting_file_paths
    }

    doc = parse_latex_from_files(
        file_reader,
        Path(input_path.name),
        supporting_file_paths=supporting_file_paths,
        supporting_files=supporting_files,
    )

    main_content, section_files = _split_document(doc, config.split)
    return (
        input_path,
        config.split,
        {
            Path(input_path.name): main_content,
            **section_files,
            **doc.supporting_files,
        },
    )


def split_command(
    input_file: Path,
    output_dir: Path,
    config_file: Path,
) -> None:
    """Execute the split command."""

    # Output directory must be empty
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"Output directory is not empty: {output_dir}")

    _validate_input_manuscript_roundtrip(input_file, config_file)

    _, _, generated_output = _generate_split_output(input_file, config_file)
    write_directory(generated_output, output_dir)
