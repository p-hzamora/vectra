"""Default locations, following the XDG base directory convention."""

import os
from pathlib import Path

APP_DIR_NAME: str = "vectra"


def _xdg_dir(variable: str, fallback: str) -> Path:
    """`$variable` when set and absolute, else `~/<fallback>`."""
    value: str = os.environ.get(variable, "")
    return Path(value) if value and Path(value).is_absolute() else Path.home() / fallback


def default_config_dir() -> Path:
    """`$XDG_CONFIG_HOME/vectra` (normally `~/.config/vectra`)."""
    return _xdg_dir("XDG_CONFIG_HOME", ".config") / APP_DIR_NAME


def default_env_file() -> Path:
    """`$XDG_CONFIG_HOME/vectra/.env` (normally `~/.config/vectra/.env`)."""
    return default_config_dir() / ".env"


def default_data_dir() -> Path:
    """`$XDG_DATA_HOME/vectra` (normally `~/.local/share/vectra`)."""
    return _xdg_dir("XDG_DATA_HOME", ".local/share") / APP_DIR_NAME
