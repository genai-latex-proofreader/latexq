import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from lq.utils.io import ensure_path_exists

type OutputWriter = Callable[[str], None]


@dataclass(frozen=True)
class OutputTarget:
    output_file: Path | None
    stdout: bool

    def __post_init__(self) -> None:
        if self.output_file is None and not self.stdout:
            raise ValueError("Either --output-file or --stdout must be provided")

        if self.output_file is not None and self.stdout:
            raise ValueError("--output-file and --stdout cannot be used together")


def get_writer(output: OutputTarget) -> OutputWriter:
    def write_stdout(text: str) -> None:
        sys.stdout.write(text)

    if output.stdout:
        return write_stdout

    output_file = output.output_file
    assert output_file is not None

    def write_output_file(text: str) -> None:
        ensure_path_exists(output_file).write_text(text)

    return write_output_file
