"""LanceDB implementation of the manifest read repository."""

from collections.abc import AsyncIterator

from vectra.bounded_context.retrieval.application.dtos import ManifestEntryDTO
from vectra.bounded_context.retrieval.application.ports.read_repositories import (
    IManifestReadRepository,
)

from .lancedb_store import MANIFEST_SCHEMA, MANIFEST_TABLE, LanceDbStore, literal


class LanceDbManifestReadRepositoryAdapter(IManifestReadRepository):
    """Streams the `manifest` rows of one collection."""

    def __init__(self, store: LanceDbStore) -> None:
        self._store: LanceDbStore = store

    async def stream(self, collection: str) -> AsyncIterator[ManifestEntryDTO]:
        def read() -> list[ManifestEntryDTO]:
            if not self._store.exists(MANIFEST_TABLE):
                return []
            rows = (
                self._store.table(MANIFEST_TABLE, MANIFEST_SCHEMA)
                .search()
                .where(f"collection = {literal(collection)}")
                .select(["path", "content_hash", "chunker_version"])
                .to_list()
            )
            return [
                ManifestEntryDTO(
                    path=row["path"],
                    content_hash=row["content_hash"],
                    chunker_version=row["chunker_version"],
                )
                for row in rows
            ]

        for entry in await self._store.run(read):
            yield entry
