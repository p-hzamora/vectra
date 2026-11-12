"""`vectra update`: check for a newer release, or reinstall at the latest one."""

import asyncio
from typing import Annotated

import typer

from vectra import __version__
from vectra.bounded_context.updates.application.dtos import UpdateAppliedDTO, UpdateCheckDTO
from vectra.bounded_context.updates.application.handlers.commands import ApplyUpdateCommand
from vectra.bounded_context.updates.application.handlers.queries import CheckForUpdateQuery
from vectra.exceptions import ConfirmationRequiredError, UsageError
from vectra.interfaces.cli import bootstrap, output
from vectra.interfaces.cli.options import JsonOption
from vectra.interfaces.cli.responses import UpdateApplyResponse, UpdateCheckResponse

COLLECTIONS_CHECK_STEP: str = (
    "Run `vectra collections check` in case the new version changed the embedding settings."
)


def update(
    check: Annotated[
        bool, typer.Option("--check", help="Only look for a newer release (the default).")
    ] = False,
    apply: Annotated[
        bool, typer.Option("--apply", help="Reinstall vectra at the latest release.")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm --apply.")] = False,
    as_json: JsonOption = False,
) -> None:
    """Check GitHub for a newer release, or with --apply --yes reinstall at it."""
    if check and apply:
        raise UsageError(
            "--check and --apply cannot be combined.",
            next_steps=["Run `vectra update --check`, or `vectra update --apply --yes`."],
        )
    if apply and not yes:
        raise ConfirmationRequiredError(
            "Updating reinstalls vectra with the installer that owns it.",
            next_steps=[
                "Run `vectra update --apply --yes`.",
                "Run `vectra update --check` to see the version and command first.",
            ],
        )
    handlers = bootstrap.build_updates()
    if apply:
        applied: UpdateAppliedDTO = asyncio.run(
            handlers.apply.handle(ApplyUpdateCommand(current=__version__))
        )
        output.emit(
            UpdateApplyResponse.model_validate(
                {
                    **applied.model_dump(),
                    "next_steps": [COLLECTIONS_CHECK_STEP] if applied.applied else [],
                }
            )
        )
        return
    checked: UpdateCheckDTO = asyncio.run(
        handlers.check.handle(CheckForUpdateQuery(current=__version__))
    )
    output.emit(UpdateCheckResponse.model_validate(checked))
