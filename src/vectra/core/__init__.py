"""Framework-agnostic configuration: typed settings and how the environment is loaded."""

from .env import Environment, load_environment, resolve_env_file

__all__ = ["Environment", "load_environment", "resolve_env_file"]
