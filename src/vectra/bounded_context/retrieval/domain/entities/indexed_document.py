"""IndexedDocument aggregate root."""

from collections.abc import Sequence
from dataclasses import dataclass

from vectra.bounded_context.retrieval.domain.value_objects import (
    ChunkId,
    CollectionName,
    ContentHash,
    SourcePath,
)


@dataclass(slots=True, kw_only=True)
class IndexedDocument:
    """What the manifest knows about one indexed document; the chunks themselves are not held.

    Attributes:
        collection: Owning collection.
        path: Document path (identity with `collection`).
        content_hash: Hash of the indexed bytes.
        chunker_version: Chunker that produced the chunks.
        chunk_ids: Ids of its chunks in document order.
    """

    collection: CollectionName
    path: SourcePath
    content_hash: ContentHash
    chunker_version: str
    chunk_ids: tuple[ChunkId, ...]

    def reindex(
        self, content_hash: ContentHash, chunker_version: str, chunk_ids: Sequence[ChunkId]
    ) -> tuple[ChunkId, ...]:
        """Record a new indexing of the document.

        Returns:
            The ids that were indexed before and are not part of the new set (stale).
        """
        kept: set[ChunkId] = set(chunk_ids)
        stale: tuple[ChunkId, ...] = tuple(
            chunk_id for chunk_id in self.chunk_ids if chunk_id not in kept
        )
        self.content_hash = content_hash
        self.chunker_version = chunker_version
        self.chunk_ids = tuple(chunk_ids)
        return stale

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, IndexedDocument)
            and other.collection == self.collection
            and other.path == self.path
        )

    def __hash__(self) -> int:
        return hash((self.collection, self.path))
