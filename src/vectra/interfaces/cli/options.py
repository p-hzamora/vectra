"""Reusable Typer option declarations, so every command spells them the same way."""

from pathlib import Path
from typing import Annotated

import typer

from . import output

JsonOption = Annotated[
    bool,
    typer.Option(
        "--json", help="Print a JSON envelope instead of text.", callback=output.remember_json_mode
    ),
]
VerboseOption = Annotated[
    bool,
    typer.Option("--verbose", "-v", help="Show progress on stderr while working."),
]
EnvFileOption = Annotated[
    Path | None,
    typer.Option(
        "--env-file",
        help="Explicit configuration file (default: ~/.config/vectra/.env).",
        dir_okay=False,
    ),
]
