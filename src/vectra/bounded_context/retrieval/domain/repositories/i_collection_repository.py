"""Write repository of the Collection aggregate."""

import abc

from vectra.bounded_context.retrieval.domain.entities import Collection
from vectra.bounded_context.retrieval.domain.value_objects import CollectionName


class ICollectionRepository(abc.ABC):
    """Loads and stores collections by name. No query methods: reads go through read repositories."""

    @abc.abstractmethod
    async def get(self, name: CollectionName) -> Collection | None:
        """The collection called `name`, or None."""
        ...

    @abc.abstractmethod
    async def save(self, collection: Collection) -> None:
        """Create the collection and its empty chunk storage (the profile never changes)."""
        ...

    @abc.abstractmethod
    async def delete(self, name: CollectionName) -> None:
        """Remove the collection with its chunks and manifest in one store call."""
        ...
