"""One module per command group; each exposes a Typer sub-application or command."""

from .config_commands import config_app
from .retrieval_commands import collections_app, search, sync
from .skills_commands import skills_app

__all__ = ["collections_app", "config_app", "search", "skills_app", "sync"]
