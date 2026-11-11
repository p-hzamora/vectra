"""`vectra sync`, `vectra search` and `vectra collections`: index folders and search them."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from vectra.bounded_context.retrieval.application.dtos import (
    CollectionListDTO,
    CollectionProfileCheckListDTO,
    DropResultDTO,
    RepairResultDTO,
    SearchResultDTO,
    SyncResultDTO,
)
from vectra.bounded_context.retrieval.application.handlers.commands import (
    DEFAULT_INCLUDE,
    DropCollectionCommand,
    RepairCollectionsCommand,
    SyncCollectionCommand,
)
from vectra.bounded_context.retrieval.application.handlers.queries import (
    CheckCollectionProfileQuery,
    ListCollectionsQuery,
    SearchCollectionQuery,
)
from vectra.exceptions import ConfirmationRequiredError, ExitCodeEnum, NewRootRequiresRebuildError
from vectra.interfaces.cli import bootstrap, output
from vectra.interfaces.cli.options import JsonOption, VerboseOption
from vectra.interfaces.cli.progress import progress_scope
from vectra.interfaces.cli.responses import (
    CollectionCheckListResponse,
    CollectionListResponse,
    DropResponse,
    RepairResponse,
    SearchResponse,
    SyncResponse,
)
from vectra.interfaces.cli.state import cli_state

collections_app: typer.Typer = typer.Typer(help="List and drop collections.", no_args_is_help=True)

NameArgument = Annotated[str, typer.Argument(help="Collection name.")]


def sync(
    context: typer.Context,
    name: NameArgument,
    root: Annotated[
        Path | None,
        typer.Argument(
            help="Folder to index (a collection keeps its first root); "
            "omit it to reuse the collection's own."
        ),
    ] = None,
    include: Annotated[
        list[str] | None, typer.Option("--include", help="Glob to index (repeatable).")
    ] = None,
    exclude: Annotated[
        list[str] | None, typer.Option("--exclude", help="Glob to skip (repeatable).")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would change; write nothing.")
    ] = False,
    allow_mass_delete: Annotated[
        bool,
        typer.Option(
            "--allow-mass-delete", help="Allow deleting more than half of the indexed documents."
        ),
    ] = False,
    rebuild: Annotated[
        bool,
        typer.Option(
            "--rebuild",
            help="Drop the collection and recreate it with the current model (keeps its root).",
        ),
    ] = False,
    new_root: Annotated[
        bool,
        typer.Option(
            "--new-root",
            help="With --rebuild, rebind the collection to this root instead of keeping its own.",
        ),
    ] = False,
    as_json: JsonOption = False,
    verbose: VerboseOption = False,
) -> int:
    """Index the changes of ROOT (default: the collection's root) into collection NAME.

    The collection is created on first use, which needs ROOT. Exit 1 if any file failed.
    """
    if new_root and not rebuild:
        raise NewRootRequiresRebuildError(
            "--new-root only applies together with --rebuild.",
            {"new_root": True, "rebuild": False},
            next_steps=["Add --rebuild, or drop --new-root."],
        )
    command = SyncCollectionCommand(
        collection=name,
        root=str(root.expanduser().resolve()) if root else None,
        include=tuple(include) if include else DEFAULT_INCLUDE,
        exclude=tuple(exclude or ()),
        dry_run=dry_run,
        allow_mass_delete=allow_mass_delete,
        rebuild=rebuild,
        allow_new_root=new_root,
    )
    with progress_scope(verbose) as progress:
        handlers = bootstrap.build_retrieval(cli_state(context).environment(), progress=progress)
        result: SyncResultDTO = asyncio.run(handlers.sync.handle(command))
    output.emit(SyncResponse.model_validate(result))
    return ExitCodeEnum.FAILURE if result.failed else ExitCodeEnum.OK


def search(
    context: typer.Context,
    name: NameArgument,
    query: Annotated[str, typer.Argument(help="What to look for, in natural language.")],
    top_k: Annotated[int, typer.Option("--top-k", help="Documents to return.")] = 5,
    path_prefix: Annotated[
        str | None, typer.Option("--path-prefix", help="Only documents under this path.")
    ] = None,
    min_score: Annotated[
        float | None, typer.Option("--min-score", help="Drop hits below this score (0..1).")
    ] = None,
    as_json: JsonOption = False,
) -> None:
    """Semantic search in collection NAME."""
    handlers = bootstrap.build_retrieval(cli_state(context).environment())
    result: SearchResultDTO = asyncio.run(
        handlers.search.handle(
            SearchCollectionQuery(
                collection=name,
                text=query,
                top_k=top_k,
                path_prefix=path_prefix,
                min_score=min_score,
            )
        )
    )
    output.emit(SearchResponse.model_validate(result))


@collections_app.command("list")
def list_collections(context: typer.Context, as_json: JsonOption = False) -> None:
    """List collections with their model, size and source root."""
    handlers = bootstrap.build_retrieval(cli_state(context).environment())
    result: CollectionListDTO = asyncio.run(
        handlers.list_collections.handle(ListCollectionsQuery())
    )
    output.emit(CollectionListResponse.model_validate(result))


@collections_app.command("check")
def check(
    context: typer.Context,
    name: Annotated[
        str | None, typer.Argument(help="Collection name; omit to check every collection.")
    ] = None,
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            help="Rebuild out-of-sync collections from their own roots (re-embeds everything).",
        ),
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm --fix.")] = False,
    as_json: JsonOption = False,
    verbose: VerboseOption = False,
) -> int:
    """Check that collections were built with the configured embedding model. Exit 1 on mismatch."""
    if fix and not yes:
        raise ConfirmationRequiredError(
            "Fixing drops and re-embeds every out-of-sync collection.",
            {"collection": name},
            next_steps=["Run `vectra collections check --fix --yes`."],
        )
    if fix:
        with progress_scope(verbose) as progress:
            handlers = bootstrap.build_retrieval(
                cli_state(context).environment(), progress=progress
            )
            repaired: RepairResultDTO = asyncio.run(
                handlers.repair.handle(RepairCollectionsCommand(collection=name))
            )
        output.emit(RepairResponse.model_validate(repaired))
        failed = repaired.skipped or any(item.failed for item in repaired.repaired)
        return ExitCodeEnum.FAILURE if failed else ExitCodeEnum.OK
    handlers = bootstrap.build_retrieval(cli_state(context).environment())
    result: CollectionProfileCheckListDTO = asyncio.run(
        handlers.check.handle(CheckCollectionProfileQuery(collection=name))
    )
    output.emit(
        CollectionCheckListResponse.model_validate(
            {
                "in_sync": result.in_sync,
                "collections": [item.model_dump() for item in result.collections],
            }
        )
    )
    return ExitCodeEnum.OK if result.in_sync else ExitCodeEnum.FAILURE


@collections_app.command("drop")
def drop(
    context: typer.Context,
    name: NameArgument,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm the deletion.")] = False,
    as_json: JsonOption = False,
) -> None:
    """Delete collection NAME with all its chunks. Requires --yes."""
    if not yes:
        raise ConfirmationRequiredError(
            f"Dropping {name!r} deletes its index and cannot be undone.",
            {"collection": name},
            next_steps=[f"Run `vectra collections drop {name} --yes`."],
        )
    handlers = bootstrap.build_retrieval(cli_state(context).environment())
    result: DropResultDTO = asyncio.run(handlers.drop.handle(DropCollectionCommand(name=name)))
    output.emit(DropResponse.model_validate(result))
