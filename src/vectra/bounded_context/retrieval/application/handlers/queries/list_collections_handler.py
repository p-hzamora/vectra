"""List collections."""

from vectra.bounded_context.retrieval.application.dtos import CollectionListDTO
from vectra.bounded_context.retrieval.application.ports.read_repositories import (
    ICollectionReadRepository,
)
from vectra.shared_kernel.application.handlers import IHandler
from vectra.utils import FrozenObject


class ListCollectionsQuery(FrozenObject):
    """List every collection."""


class ListCollectionsHandler(IHandler[ListCollectionsQuery, CollectionListDTO]):
    """Every collection with its status."""

    def __init__(self, *, read_repository: ICollectionReadRepository) -> None:
        self._read_repository: ICollectionReadRepository = read_repository

    async def handle(self, action: ListCollectionsQuery) -> CollectionListDTO:
        """The collections."""
        return CollectionListDTO(collections=tuple(await self._read_repository.list_collections()))
