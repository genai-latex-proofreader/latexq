from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

type SupportingFilePattern = str


class Granularity(str, Enum):
    section = "section"
    subsection = "subsection"


class SplitConfig(BaseModel):
    """Configuration for the lq split command."""

    model_config = ConfigDict(extra="forbid")

    # Split granularity setting determines:
    # - 'section': output each section (including subsections) into a separate file.
    # - 'subsection': output each section and subsection into a separate file.
    granularity: Granularity

    # Relative subdirectories in the output directory where to write section/appendix
    # files are written:
    main_sections_dir: str
    appendix_sections_dir: str

    # Optional list of file patterns copied to output and kept unexpanded
    # when referenced by \input{...}. Supports relative paths and wildcards.
    supporting_files: list[SupportingFilePattern] = Field(default_factory=list)
