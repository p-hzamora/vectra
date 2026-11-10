"""LanceDB implementation of the collection read repository."""

from datetime import UTC

from vectra.bounded_context.retrieval.application.dtos import CollectionStatusDTO
from vectra.bounded_context.retrieval.application.ports.read_repositories import (
    ICollectionReadRepository,
)

from .lancedb_store import (
    COLLECTIONS_SCHEMA,
    COLLECTIONS_TABLE,
    MANIFEST_SCHEMA,
    MANIFEST_TABLE,
    LanceDbStore,
    literal,
)


class LanceDbCollectionReadRepositoryAdapter(ICollectionReadRepository):
    """Reads the `collections` table and counts documents and chunks."""

    def __init__(self, store: LanceDbStore) -> None:
        self._store: LanceDbStore = store

    async def list_collections(self) -> list[CollectionStatusDTO]:
        def read() -> list[CollectionStatusDTO]:
            if not self._store.exists(COLLECTIONS_TABLE):
                return []
            rows = self._store.table(COLLECTIONS_TABLE, COLLECTIONS_SCHEMA).search().to_list()
            return sorted((self._status(row) for row in rows), key=lambda status: status.name)

        return await self._store.run(read)

    async def get_status(self, name: str) -> CollectionStatusDTO | None:
        def read() -> CollectionStatusDTO | None:
            if not self._store.exists(COLLECTIONS_TABLE):
                return None
            rows = (
                self._store.table(COLLECTIONS_TABLE, COLLECTIONS_SCHEMA)
                .search()
                .where(f"name = {literal(name)}")
                .limit(1)
                .to_list()
            )
            return self._status(rows[0]) if rows else None

        return await self._store.run(read)

    def _status(self, row: dict[str, object]) -> CollectionStatusDTO:
        name = str(row["name"])
        documents: int = 0
        if self._store.exists(MANIFEST_TABLE):
            documents = self._store.table(MANIFEST_TABLE, MANIFEST_SCHEMA).count_rows(
                f"collection = {literal(name)}"
            )
        chunks_table = self._store.open_chunks(name)
        created_at = row["created_at"]
        return CollectionStatusDTO(
            name=name,
            model_id=str(row["model_id"]),
            dimension=int(str(row["dimension"])),
            source_root=str(row["source_root"]),
            created_at=created_at.astimezone(UTC),  # type: ignore[attr-defined]
            document_count=documents,
            chunk_count=chunks_table.count_rows() if chunks_table is not None else 0,
        )
