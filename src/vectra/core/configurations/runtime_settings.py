"""Where vectra keeps its data."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from .base_settings import AppBaseSettings
from .paths import default_data_dir


class RuntimeSettings(AppBaseSettings):
    """Process-wide locations.

    Attributes:
        data_dir: Folder for vectra's data, including the vector index (`VECTRA_DATA_DIR`).
    """

    model_config = SettingsConfigDict(env_prefix="VECTRA_")

    data_dir: Path = Field(default_factory=default_data_dir)
