"""LanceDB implementation of the indexed-document write repository."""

import json
from collections.abc import Sequence

from vectra.bounded_context.retrieval.domain.entities import IndexedDocument
from vectra.bounded_context.retrieval.domain.repositories import IIndexedDocumentRepository
from vectra.bounded_context.retrieval.domain.value_objects import (
    ChunkId,
    CollectionName,
    ContentHash,
    EmbeddedChunk,
    SourcePath,
)
from vectra.exceptions import VectorStoreError

from .lancedb_store import (
    MANIFEST_SCHEMA,
    MANIFEST_TABLE,
    LanceDbStore,
    literal,
)


class LanceDbIndexedDocumentRepositoryAdapter(IIndexedDocumentRepository):
    """Per document: upsert chunks, delete stale chunks, write the manifest row last."""

    def __init__(self, store: LanceDbStore) -> None:
        self._store: LanceDbStore = store

    def _manifest_filter(self, collection: CollectionName, path: SourcePath) -> str:
        return f"collection = {literal(collection.value)} AND path = {literal(path.value)}"

    async def get(self, collection: CollectionName, path: SourcePath) -> IndexedDocument | None:
        def read() -> IndexedDocument | None:
            if not self._store.exists(MANIFEST_TABLE):
                return None
            rows = (
                self._store.table(MANIFEST_TABLE, MANIFEST_SCHEMA)
                .search()
                .where(self._manifest_filter(collection, path))
                .limit(1)
                .to_list()
            )
            if not rows:
                return None
            row = rows[0]
            return IndexedDocument(
                collection=collection,
                path=path,
                content_hash=ContentHash(value=row["content_hash"]),
                chunker_version=row["chunker_version"],
                chunk_ids=tuple(ChunkId(value=value) for value in row["chunk_ids"]),
            )

        return await self._store.run(read)

    async def save(self, document: IndexedDocument, chunks: Sequence[EmbeddedChunk]) -> None:
        def write() -> None:
            table = self._store.open_chunks(document.collection.value)
            if table is None:
                raise VectorStoreError(
                    f"Collection {document.collection} has no chunk table.",
                    {"collection": document.collection.value},
                )
            if chunks:
                table.merge_insert(
                    "chunk_id"
                ).when_matched_update_all().when_not_matched_insert_all().execute(
                    [
                        {
                            "chunk_id": chunk.chunk_id.value,
                            "path": document.path.value,
                            "heading_path": list(chunk.heading_path.parts),
                            "text": chunk.text,
                            "metadata": json.dumps(chunk.metadata, sort_keys=True),
                            "vector": list(chunk.embedding.values),
                        }
                        for chunk in chunks
                    ]
                )
            keep: str = ", ".join(literal(chunk_id.value) for chunk_id in document.chunk_ids)
            stale: str = f"path = {literal(document.path.value)}"
            table.delete(f"{stale} AND chunk_id NOT IN ({keep})" if keep else stale)
            manifest = self._store.table(MANIFEST_TABLE, MANIFEST_SCHEMA)
            manifest.delete(self._manifest_filter(document.collection, document.path))
            manifest.add(
                [
                    {
                        "collection": document.collection.value,
                        "path": document.path.value,
                        "content_hash": document.content_hash.value,
                        "chunker_version": document.chunker_version,
                        "chunk_ids": [chunk_id.value for chunk_id in document.chunk_ids],
                    }
                ]
            )

        await self._store.run(write)

    async def delete(self, collection: CollectionName, path: SourcePath) -> None:
        def remove() -> None:
            table = self._store.open_chunks(collection.value)
            if table is not None:
                table.delete(f"path = {literal(path.value)}")
            if self._store.exists(MANIFEST_TABLE):
                self._store.table(MANIFEST_TABLE, MANIFEST_SCHEMA).delete(
                    self._manifest_filter(collection, path)
                )

        await self._store.run(remove)
