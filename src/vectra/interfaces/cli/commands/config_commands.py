"""`vectra config`: inspect the configuration this invocation resolves."""

import typer

from vectra.core import Environment
from vectra.interfaces.cli import output
from vectra.interfaces.cli.options import JsonOption
from vectra.interfaces.cli.responses import ConfigShowResponse
from vectra.interfaces.cli.state import cli_state

config_app: typer.Typer = typer.Typer(help="Inspect vectra's configuration.", no_args_is_help=True)


@config_app.command("show")
def show(context: typer.Context, as_json: JsonOption = False) -> None:
    """Show the configuration file read and the resolved settings."""
    environment: Environment = cli_state(context).environment()
    output.emit(
        ConfigShowResponse(
            env_file=str(environment.env_file),
            env_file_exists=environment.env_file.is_file(),
            data_dir=str(environment.runtime.data_dir),
        )
    )
