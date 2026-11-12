"""`vectra config`: inspect or create the configuration this invocation resolves."""

import asyncio
from typing import Annotated

import typer

from vectra.bounded_context.configuration.application.dtos import EnvFileInitResultDTO
from vectra.bounded_context.configuration.application.handlers.commands import InitEnvFileCommand
from vectra.core import Environment, resolve_env_file
from vectra.interfaces.cli import bootstrap, output
from vectra.interfaces.cli.options import JsonOption
from vectra.interfaces.cli.responses import ConfigInitResponse, ConfigShowResponse
from vectra.interfaces.cli.state import cli_state

config_app: typer.Typer = typer.Typer(
    help="Inspect or create vectra's configuration.", no_args_is_help=True
)


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


@config_app.command("init")
def init(
    context: typer.Context,
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing file.")] = False,
    as_json: JsonOption = False,
) -> None:
    """Write a commented env file template (default: ~/.config/vectra/.env)."""
    command = InitEnvFileCommand(
        env_file=resolve_env_file(cli_state(context).env_file), force=force
    )
    result: EnvFileInitResultDTO = asyncio.run(bootstrap.build_configuration().init.handle(command))
    output.emit(ConfigInitResponse.model_validate(result))
