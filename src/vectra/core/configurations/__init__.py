"""Typed settings, one class per concern, all sharing `AppBaseSettings`'s loading policy.

Only `vectra.core.env` builds them; everything else reads them from there.
"""

from .base_settings import AppBaseSettings
from .paths import default_config_dir, default_data_dir, default_env_file
from .retrieval_settings import RetrievalSettings
from .runtime_settings import RuntimeSettings

__all__ = [
    "AppBaseSettings",
    "RetrievalSettings",
    "RuntimeSettings",
    "default_config_dir",
    "default_data_dir",
    "default_env_file",
]
