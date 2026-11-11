"""Removes one indexed document."""

from collections.abc import Callable

from vectra.bounded_context.retrieval.application.ports.uow import IRetrievalUnitOfWork
from vectra.bounded_context.retrieval.domain.value_objects import CollectionName, SourcePath


class DocumentRemover:
    """Deletes a document's chunks and manifest entry in one unit of work."""

    def __init__(self, *, uow_factory: Callable[[], IRetrievalUnitOfWork]) -> None:
        self._uow_factory: Callable[[], IRetrievalUnitOfWork] = uow_factory

    async def remove(self, name: CollectionName, path: SourcePath) -> None:
        """Delete the document from the collection."""
        async with self._uow_factory() as uow:
            await uow.documents.delete(name, path)
            await uow.commit()
