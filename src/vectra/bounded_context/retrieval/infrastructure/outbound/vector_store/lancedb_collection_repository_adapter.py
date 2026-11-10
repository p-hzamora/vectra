"""LanceDB implementation of the collection write repository."""

from datetime import UTC

from vectra.bounded_context.retrieval.domain.entities import Collection
from vectra.bounded_context.retrieval.domain.repositories import ICollectionRepository
from vectra.bounded_context.retrieval.domain.value_objects import (
    CollectionName,
    EmbeddingProfile,
    SourceRoot,
)

from .lancedb_store import (
    CHUNKS_PREFIX,
    COLLECTIONS_SCHEMA,
    COLLECTIONS_TABLE,
    MANIFEST_SCHEMA,
    MANIFEST_TABLE,
    LanceDbStore,
    chunks_schema,
    literal,
)


class LanceDbCollectionRepositoryAdapter(ICollectionRepository):
    """Collection metadata lives in the `collections` table, chunks in `chunks_<name>`."""

    def __init__(self, store: LanceDbStore) -> None:
        self._store: LanceDbStore = store

    async def get(self, name: CollectionName) -> Collection | None:
        def read() -> Collection | None:
            if not self._store.exists(COLLECTIONS_TABLE):
                return None
            rows = (
                self._store.table(COLLECTIONS_TABLE, COLLECTIONS_SCHEMA)
                .search()
                .where(f"name = {literal(name.value)}")
                .limit(1)
                .to_list()
            )
            if not rows:
                return None
            row = rows[0]
            return Collection(
                name=name,
                profile=EmbeddingProfile(model_id=row["model_id"], dimension=row["dimension"]),
                source_root=SourceRoot(value=row["source_root"]),
                created_at=row["created_at"].astimezone(UTC),
            )

        return await self._store.run(read)

    async def save(self, collection: Collection) -> None:
        def write() -> None:
            self._store.table(
                CHUNKS_PREFIX + collection.name.value, chunks_schema(collection.profile.dimension)
            )
            table = self._store.table(COLLECTIONS_TABLE, COLLECTIONS_SCHEMA)
            table.delete(f"name = {literal(collection.name.value)}")
            table.add(
                [
                    {
                        "name": collection.name.value,
                        "model_id": collection.profile.model_id,
                        "dimension": collection.profile.dimension,
                        "source_root": collection.source_root.value,
                        "created_at": collection.created_at,
                    }
                ],
            )

        await self._store.run(write)

    async def delete(self, name: CollectionName) -> None:
        def remove() -> None:
            connection = self._store.connection()
            chunks: str = CHUNKS_PREFIX + name.value
            if self._store.exists(chunks):
                connection.drop_table(chunks)
            if self._store.exists(MANIFEST_TABLE):
                self._store.table(MANIFEST_TABLE, MANIFEST_SCHEMA).delete(
                    f"collection = {literal(name.value)}"
                )
            if self._store.exists(COLLECTIONS_TABLE):
                self._store.table(COLLECTIONS_TABLE, COLLECTIONS_SCHEMA).delete(
                    f"name = {literal(name.value)}"
                )

        await self._store.run(remove)
