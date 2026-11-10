"""Remove a collection and everything indexed in it."""

from collections.abc import Callable

from vectra.bounded_context.retrieval.application.dtos import DropResultDTO
from vectra.bounded_context.retrieval.application.ports.read_repositories import (
    ICollectionReadRepository,
)
from vectra.bounded_context.retrieval.application.ports.uow import IRetrievalUnitOfWork
from vectra.bounded_context.retrieval.domain.value_objects import CollectionName
from vectra.exceptions import CollectionNotFoundError
from vectra.shared_kernel.application.handlers import IHandler
from vectra.utils import FrozenObject


class DropCollectionCommand(FrozenObject):
    """Drop a collection.

    Attributes:
        name: Collection name.
    """

    name: str


class DropCollectionHandler(IHandler[DropCollectionCommand, DropResultDTO]):
    """Deletes the collection with its chunks and manifest."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], IRetrievalUnitOfWork],
        read_repository: ICollectionReadRepository,
    ) -> None:
        self._uow_factory: Callable[[], IRetrievalUnitOfWork] = uow_factory
        self._read_repository: ICollectionReadRepository = read_repository

    async def handle(self, action: DropCollectionCommand) -> DropResultDTO:
        """Drop the collection.

        Raises:
            CollectionNotFoundError: There is no such collection.
        """
        name = CollectionName(value=action.name)
        status = await self._read_repository.get_status(name.value)
        if status is None:
            raise CollectionNotFoundError(
                f"No collection named {name.value!r}.",
                {"collection": name.value},
                next_steps=["Run `vectra collections list`."],
            )
        async with self._uow_factory() as uow:
            await uow.collections.delete(name)
            await uow.commit()
        return DropResultDTO(
            name=name.value, documents=status.document_count, chunks=status.chunk_count
        )
