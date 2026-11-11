"""The `vectra` command: root Typer application, global options, and error handling."""

import sys
from collections.abc import Sequence
from typing import Annotated

import typer

from vectra import __version__
from vectra.exceptions import AppException, ExitCodeEnum, UsageError
from vectra.interfaces.cli import commands

from . import output
from .options import EnvFileOption
from .state import CliState

PROGRAM: str = "vectra"
EPILOG: str = (
    "Every command accepts --json and --help. "
    "Exit codes: 0 ok, 1 the operation failed, 2 invalid command line."
)

app: typer.Typer = typer.Typer(
    name=PROGRAM,
    help="Chunk files, embed them into a vector store, and serve semantic search.",
    epilog=EPILOG,
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)
app.add_typer(commands.skills_app, name="skills")
app.add_typer(commands.config_app, name="config")
app.add_typer(commands.collections_app, name="collections")
app.command("sync")(commands.sync)
app.command("search")(commands.search)


def _print_version(enabled: bool) -> None:
    """Eager `--version` callback."""
    if enabled:
        sys.stdout.write(f"{PROGRAM} {__version__}\n")
        raise typer.Exit()


@app.callback()
def root(
    context: typer.Context,
    env_file: EnvFileOption = None,
    version: Annotated[
        bool,
        typer.Option(
            "--version", help="Show the version and exit.", callback=_print_version, is_eager=True
        ),
    ] = False,
) -> None:
    """Chunk files, embed them into a vector store, and serve semantic search."""
    context.obj = CliState(env_file=env_file)


def _usage_error(error: typer.TyperException, argv: Sequence[str]) -> int:
    """Report a command-line mistake: the JSON envelope with `--json`, Typer's usage text otherwise."""
    exit_code: int = int(getattr(error, "exit_code", ExitCodeEnum.USAGE))
    if "--json" not in argv:
        show: object = getattr(error, "show", None)
        if callable(show):
            show()
        return exit_code
    output.remember_json_mode(True)
    context: object = getattr(error, "ctx", None)
    format_message: object = getattr(error, "format_message", None)
    message: str = str(format_message() if callable(format_message) else error)
    command_path: str = str(getattr(context, "command_path", PROGRAM))
    output.emit_error(
        UsageError(
            message,
            next_steps=[f"Run `{command_path} --help` to see the arguments and options."],
        )
    )
    return exit_code


def run(argv: Sequence[str]) -> int:
    """Run one command line and return its exit code (the testable entry point).

    Args:
        argv: Arguments after the program name.

    Returns:
        The exit code (see `ExitCodeEnum`).
    """
    with output.output_scope():
        try:
            result: object = app(args=list(argv), prog_name=PROGRAM, standalone_mode=False)
        except typer.Abort:
            return ExitCodeEnum.FAILURE
        except typer.TyperException as error:  # usage errors raised by Typer's bundled click
            return _usage_error(error, argv)
        except AppException as error:
            output.emit_error(error)
            return error.exit_code
        return result if isinstance(result, int) else ExitCodeEnum.OK


def main() -> None:
    """Console-script entry point."""
    sys.exit(run(sys.argv[1:]))
