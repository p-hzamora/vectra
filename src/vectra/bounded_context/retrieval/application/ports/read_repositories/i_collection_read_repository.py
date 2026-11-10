"""Read model of collections."""

import abc

from vectra.bounded_context.retrieval.application.dtos import CollectionStatusDTO


class ICollectionReadRepository(abc.ABC):
    """Lists collections and reports their status."""

    @abc.abstractmethod
    async def list_collections(self) -> list[CollectionStatusDTO]:
        """Every collection, sorted by name."""
        ...

    @abc.abstractmethod
    async def get_status(self, name: str) -> CollectionStatusDTO | None:
        """The status of `name`, or None when there is no such collection."""
        ...
