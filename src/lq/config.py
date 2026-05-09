from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from lq.split.data_model import SplitConfig


class LatexqConfig(BaseModel):
    """Top-level latexq configuration file model."""

    model_config = ConfigDict(extra="forbid")

    split: SplitConfig


def load_config(config_path: Path) -> LatexqConfig:
    """Load a lq config from a YAML file."""
    data = yaml.safe_load(config_path.read_text())
    return LatexqConfig.model_validate(data)


def save_config(config: LatexqConfig, config_path: Path) -> None:
    """Write a lq config to a YAML file."""
    data = config.model_dump(mode="json")
    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
