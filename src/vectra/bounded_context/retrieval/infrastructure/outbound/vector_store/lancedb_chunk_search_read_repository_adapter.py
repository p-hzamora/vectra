"""LanceDB implementation of the chunk search read repository."""

from collections.abc import Sequence
from typing import cast

from lancedb.query import LanceVectorQueryBuilder

from vectra.bounded_context.retrieval.application.dtos import ChunkHitDTO
from vectra.bounded_context.retrieval.application.ports.read_repositories import (
    IChunkSearchReadRepository,
)

from .lancedb_store import LanceDbStore, literal


class LanceDbChunkSearchReadRepositoryAdapter(IChunkSearchReadRepository):
    """Cosine nearest-neighbour search. Score is `1 - cosine distance`, clamped to 0..1."""

    def __init__(self, store: LanceDbStore) -> None:
        self._store: LanceDbStore = store

    async def search(
        self, collection: str, vector: Sequence[float], path_prefix: str | None, limit: int
    ) -> list[ChunkHitDTO]:
        def read() -> list[ChunkHitDTO]:
            table = self._store.open_chunks(collection)
            if table is None:
                return []
            query = (
                cast(LanceVectorQueryBuilder, table.search(list(vector)))
                .metric("cosine")
                .limit(limit)
            )
            if path_prefix:
                query = query.where(f"starts_with(path, {literal(path_prefix)})", prefilter=True)
            return [
                ChunkHitDTO(
                    chunk_id=row["chunk_id"],
                    path=row["path"],
                    heading_path=tuple(row["heading_path"]),
                    text=row["text"],
                    score=min(1.0, max(0.0, 1.0 - float(row["_distance"]))),
                )
                for row in query.to_list()
            ]

        return await self._store.run(read)
