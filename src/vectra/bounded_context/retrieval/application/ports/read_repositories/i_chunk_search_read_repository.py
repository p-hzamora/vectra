"""Read model for vector search."""

import abc
from collections.abc import Sequence

from vectra.bounded_context.retrieval.application.dtos import ChunkHitDTO


class IChunkSearchReadRepository(abc.ABC):
    """Nearest-chunk search."""

    @abc.abstractmethod
    async def search(
        self, collection: str, vector: Sequence[float], path_prefix: str | None, limit: int
    ) -> list[ChunkHitDTO]:
        """Up to `limit` nearest chunks, best first; scores are normalized to 0..1 (higher is
        better) by the adapter."""
        ...
