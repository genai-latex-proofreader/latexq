from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from lq.config import LatexqConfig, load_config, save_config
from lq.split.data_model import (
    Granularity,
    SplitConfig,
)

DEFAULT_LQ_CONFIG = LatexqConfig(
    split=SplitConfig(
        granularity=Granularity.section,
        main_sections_dir="sections",
        appendix_sections_dir="appendix",
    )
)


# --- load_config ---


def test_load_existing_config(tmp_path: Path):
    config_path = tmp_path / "lq.yaml"
    config_path.write_text("""\
split:
  granularity: subsection
  main_sections_dir: chapters
  appendix_sections_dir: back
""")

    config = load_config(config_path)

    assert config.split.granularity == Granularity.subsection
    assert config.split.main_sections_dir == "chapters"
    assert config.split.appendix_sections_dir == "back"


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("", id="empty"),
        pytest.param("- item1\n- item2\n", id="list"),
        pytest.param("just a string\n", id="scalar"),
    ],
)
def test_load_rejects_non_mapping(tmp_path: Path, content: str):
    config_path = tmp_path / "lq.yaml"
    config_path.write_text(content)

    with pytest.raises(ValidationError):
        load_config(config_path)


def test_load_rejects_missing_split_key(tmp_path: Path):
    config_path = tmp_path / "lq.yaml"
    config_path.write_text("granularity: section\n")

    with pytest.raises(Exception):
        load_config(config_path)


def test_load_rejects_missing_split_fields(tmp_path: Path):
    config_path = tmp_path / "lq.yaml"
    config_path.write_text("split:\n  granularity: section\n")

    with pytest.raises(Exception):
        load_config(config_path)


def test_load_rejects_invalid_granularity(tmp_path: Path):
    config_path = tmp_path / "lq.yaml"
    save_config(DEFAULT_LQ_CONFIG, config_path)
    data = yaml.safe_load(config_path.read_text())
    data["split"]["granularity"] = "paragraph"
    config_path.write_text(yaml.dump(data))

    with pytest.raises(Exception):
        load_config(config_path)


def test_load_rejects_extra_top_level_fields(tmp_path: Path):
    config_path = tmp_path / "lq.yaml"
    save_config(DEFAULT_LQ_CONFIG, config_path)
    data = yaml.safe_load(config_path.read_text())
    data["unknown_field"] = "surprise"
    config_path.write_text(yaml.dump(data))

    with pytest.raises(Exception):
        load_config(config_path)


def test_load_rejects_extra_split_fields(tmp_path: Path):
    config_path = tmp_path / "lq.yaml"
    save_config(DEFAULT_LQ_CONFIG, config_path)
    data = yaml.safe_load(config_path.read_text())
    data["split"]["unknown_field"] = "surprise"
    config_path.write_text(yaml.dump(data))

    with pytest.raises(Exception):
        load_config(config_path)


# --- save_config ---


def test_save_roundtrip(tmp_path: Path):
    config_path = tmp_path / "lq.yaml"
    split = SplitConfig(
        granularity=Granularity.subsection,
        main_sections_dir="chapters",
        appendix_sections_dir="back",
    )
    original = LatexqConfig(split=split)

    save_config(original, config_path)
    loaded = load_config(config_path)

    assert loaded == original


def test_save_overwrites_existing(tmp_path: Path):
    config_path = tmp_path / "lq.yaml"
    save_config(DEFAULT_LQ_CONFIG, config_path)

    updated_split = DEFAULT_LQ_CONFIG.split.model_copy(
        update={"main_sections_dir": "chapters"}
    )
    save_config(LatexqConfig(split=updated_split), config_path)
    loaded = load_config(config_path)

    assert loaded.split.main_sections_dir == "chapters"
