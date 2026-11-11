"""Rebuild the collections whose embedding model differs from the configured one."""

from vectra.bounded_context.retrieval.application.dtos import (
    RepairResultDTO,
    SkippedCollectionDTO,
    SyncResultDTO,
)
from vectra.bounded_context.retrieval.application.handlers.queries import (
    CheckCollectionProfileHandler,
    CheckCollectionProfileQuery,
)
from vectra.bounded_context.retrieval.application.ports.progress import IProgress, NullProgress
from vectra.exceptions import AppException
from vectra.shared_kernel.application.handlers import IHandler
from vectra.utils import FrozenObject

from .sync_collection_handler import SyncCollectionCommand, SyncCollectionHandler


class RepairCollectionsCommand(FrozenObject):
    """Rebuild out-of-sync collections from their own roots.

    Attributes:
        collection: Collection name; `None` repairs every out-of-sync collection.
    """

    collection: str | None = None


class RepairCollectionsHandler(IHandler[RepairCollectionsCommand, RepairResultDTO]):
    """Runs a rebuild sync per out-of-sync collection; one failure never stops the rest."""

    def __init__(
        self,
        *,
        check: CheckCollectionProfileHandler,
        sync: SyncCollectionHandler,
        progress: IProgress | None = None,
    ) -> None:
        self._check: CheckCollectionProfileHandler = check
        self._sync: SyncCollectionHandler = sync
        self._progress: IProgress = progress or NullProgress()

    async def handle(self, action: RepairCollectionsCommand) -> RepairResultDTO:
        """The collections rebuilt and the ones skipped.

        Raises:
            CollectionNotFoundError: A name was given and there is no such collection.
        """
        checked = await self._check.handle(
            CheckCollectionProfileQuery(collection=action.collection)
        )
        repaired: list[SyncResultDTO] = []
        skipped: list[SkippedCollectionDTO] = []
        for item in checked.collections:
            if item.in_sync:
                self._progress.report(f"{item.name}: in sync, left alone")
                continue
            self._progress.report(
                f"{item.name}: built with {item.model_id}:{item.dimension}, configured "
                f"{item.configured_model_id}:{item.configured_dimension}; rebuilding"
            )
            try:
                repaired.append(
                    await self._sync.handle(
                        SyncCollectionCommand(collection=item.name, rebuild=True)
                    )
                )
            except AppException as error:
                self._progress.report(f"{item.name}: skipped [{error.error_code}]")
                skipped.append(
                    SkippedCollectionDTO(
                        name=item.name, code=error.error_code, message=error.message
                    )
                )
        return RepairResultDTO(repaired=tuple(repaired), skipped=tuple(skipped))
