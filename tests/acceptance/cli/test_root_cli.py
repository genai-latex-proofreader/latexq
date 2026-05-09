import pytest

from lq import __version__
from tests.utils import run_lq_cli


def test_args_empty(capsys):
    with pytest.raises(SystemExit) as excinfo:
        run_lq_cli()

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "the following arguments are required: command" in captured.err


def test_help_lists_subcommands(capsys):
    with pytest.raises(SystemExit) as excinfo:
        run_lq_cli("--help")

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "flatten" in captured.out
    assert "select" in captured.out
    assert "graph" in captured.out
    assert "split" in captured.out


def test_args_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        run_lq_cli("--version")

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == f"lq version {__version__}"
