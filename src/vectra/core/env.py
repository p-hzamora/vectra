"""The single entry point to vectra configuration.

Every settings class in `vectra.core.configurations` is built here and nowhere else: the
interfaces read `.env` values and default locations only through this module. The `.env`
path is chosen per invocation (`--env-file`), so settings are loaded by `load_environment`
instead of at import time.
"""

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from vectra.exceptions import InvalidConfigurationError
from vectra.shared_kernel.domain import JsonValue

from .configurations import AppBaseSettings, RuntimeSettings, default_env_file


@dataclass(frozen=True, slots=True, kw_only=True)
class Environment:
    """All vectra settings of one process.

    Attributes:
        env_file: The `.env` file that was read (it may not exist).
        runtime: Data locations.
    """

    env_file: Path
    runtime: RuntimeSettings


def load_environment(env_file: Path | None = None) -> Environment:
    """Read settings from `env_file` (default `~/.config/vectra/.env`) and the environment.

    Environment variables override values from the file.

    Args:
        env_file: `.env` file to read; a missing file is fine.

    Returns:
        The validated settings.

    Raises:
        InvalidConfigurationError: A value failed validation.
    """
    path: Path = (env_file or default_env_file()).expanduser()
    problems: list[JsonValue] = []
    runtime: RuntimeSettings | None = _load(RuntimeSettings, path, problems)
    if runtime is None:
        raise InvalidConfigurationError(
            f"Invalid configuration in {path} or the environment.",
            {"env_file": str(path), "problems": problems},
            next_steps=[f"Fix the variables listed in 'problems' (in {path} or the environment)."],
        )
    return Environment(env_file=path, runtime=runtime)


def _load[S: AppBaseSettings](
    settings_class: type[S], env_file: Path, problems: list[JsonValue]
) -> S | None:
    """Build one settings class, appending `VARIABLE: reason` lines to `problems` on failure."""
    try:
        return settings_class(_env_file=env_file)
    except ValidationError as error:
        prefix: str = str(settings_class.model_config.get("env_prefix", ""))
        problems.extend(
            f"{prefix}{'_'.join(str(part) for part in issue['loc']).upper()}: {issue['msg']}"
            for issue in error.errors()
        )
        return None
