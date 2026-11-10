"""Per-invocation CLI state shared between the root callback and the commands."""

from dataclasses import dataclass
from pathlib import Path

import typer

from vectra.core import Environment, load_environment


@dataclass(slots=True, kw_only=True)
class CliState:
    """What the root callback parsed.

    Attributes:
        env_file: Explicit configuration file, or None for the default location.
    """

    env_file: Path | None = None

    def environment(self) -> Environment:
        """Load the settings for this invocation."""
        return load_environment(self.env_file)


def cli_state(context: typer.Context) -> CliState:
    """The `CliState` stored by the root callback (a fresh one when invoked directly)."""
    state: object = context.find_root().obj
    return state if isinstance(state, CliState) else CliState()
