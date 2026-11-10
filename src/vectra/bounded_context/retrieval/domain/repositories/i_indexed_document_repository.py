"""Write repository of the IndexedDocument aggregate."""

import abc
from collections.abc import Sequence

from vectra.bounded_context.retrieval.domain.entities import IndexedDocument
from vectra.bounded_context.retrieval.domain.value_objects import (
    CollectionName,
    EmbeddedChunk,
    SourcePath,
)


class IIndexedDocumentRepository(abc.ABC):
    """Loads and stores indexed documents together with their chunks."""

    @abc.abstractmethod
    async def get(self, collection: CollectionName, path: SourcePath) -> IndexedDocument | None:
        """The manifest entry of `path`, or None."""
        ...

    @abc.abstractmethod
    async def save(self, document: IndexedDocument, chunks: Sequence[EmbeddedChunk]) -> None:
        """Write one document: upsert `chunks`, delete the document's chunks not in
        `document.chunk_ids`, and write the manifest entry last (so a crash re-syncs it)."""
        ...

    @abc.abstractmethod
    async def delete(self, collection: CollectionName, path: SourcePath) -> None:
        """Delete the document's chunks, then its manifest entry last."""
        ...
