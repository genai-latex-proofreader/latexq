from pathlib import Path

import pytest

from lq.utils.output import OutputTarget, get_writer


def test_output_uses_stdout_writer(capsys):
    writer = get_writer(OutputTarget(output_file=None, stdout=True))

    writer("hello")

    captured = capsys.readouterr()
    assert captured.out == "hello"
    assert captured.err == ""


def test_output_uses_file_writer(tmp_path: Path):
    output_file = tmp_path / "out.tex"

    writer = get_writer(OutputTarget(output_file=output_file, stdout=False))
    writer("hello")

    assert output_file.read_text() == "hello"


def test_output_rejects_file_and_stdout_together():
    with pytest.raises(ValueError, match="cannot be used together"):
        OutputTarget(output_file=Path("out.tex"), stdout=True)


def test_output_requires_explicit_destination():
    with pytest.raises(ValueError, match="must be provided"):
        OutputTarget(output_file=None, stdout=False)
