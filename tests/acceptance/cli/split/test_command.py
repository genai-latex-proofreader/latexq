from pathlib import Path

import pytest

from lq.config import save_config
from lq.latex_interface.roundtrip import LatexRoundtripValidationError
from lq.split.data_model import Granularity
from lq.utils.io import write_directory

from ....utils import run_lq_cli
from .helpers import LATEX_WITHOUT_APPENDIX, make_split_config, run_split


def test_split_rejects_nonempty_output_dir(tmp_path: Path):
    input_file = tmp_path / "test.tex"
    out_dir = tmp_path / "out"
    write_directory(
        {
            Path("test.tex"): LATEX_WITHOUT_APPENDIX,
            Path("out/existing.txt"): "blocker",
        },
        tmp_path,
    )

    with pytest.raises(SystemExit):
        run_split(input_file, out_dir, make_split_config(Granularity.section))


@pytest.mark.parametrize(
    ("args", "expected_error"),
    [
        pytest.param(
            ("--input-file", "paper.tex", "--output-dir", "out"),
            "--config-file",
            id="requires-config-file",
        ),
        pytest.param(
            ("--input-file", "paper.tex", "--config-file", "lq.yaml"),
            "--output-dir",
            id="requires-output-dir-without-validate",
        ),
        pytest.param(
            (
                "--input-file",
                "paper.tex",
                "--output-dir",
                "out",
                "--config-file",
                "lq.yaml",
                "--validate",
            ),
            "cannot be used with --validate",
            id="validate-rejects-output-dir",
        ),
    ],
)
def test_split_cli_argument_validation(
    capsys,
    args: tuple[str, ...],
    expected_error: str,
):
    with pytest.raises(SystemExit) as excinfo:
        run_lq_cli("split", *args)

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert expected_error in captured.err


def test_split_refuses_to_write_when_input_roundtrip_validation_fails(
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
):
    write_directory({Path("test.tex"): LATEX_WITHOUT_APPENDIX}, tmp_path)

    input_file = tmp_path / "test.tex"
    output_dir = tmp_path / "out"
    config = make_split_config(Granularity.section)
    config_file = tmp_path / "lq.yaml"
    save_config(config, config_file)

    def raise_validation_error(_: str) -> None:
        raise LatexRoundtripValidationError("simulated manuscript validation failure")

    monkeypatch.setattr(
        "lq.split.command.validate_latex_roundtrip",
        raise_validation_error,
    )

    with pytest.raises(SystemExit) as excinfo:
        run_lq_cli(
            "split",
            "--input-file",
            str(input_file),
            "--output-dir",
            str(output_dir),
            "--config-file",
            str(config_file),
        )

    assert excinfo.value.code == 2
    assert not output_dir.exists()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "input manuscript failed roundtrip validation" in captured.err
    assert "simulated manuscript validation failure" in captured.err
