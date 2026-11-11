"""Semantic search over one collection."""

from vectra.bounded_context.retrieval.application.dtos import (
    ChunkHitDTO,
    CollectionProfileCheckDTO,
    SearchResultDTO,
)
from vectra.bounded_context.retrieval.application.ports.embedding import IEmbedder
from vectra.bounded_context.retrieval.application.ports.read_repositories import (
    IChunkSearchReadRepository,
)
from vectra.bounded_context.retrieval.application.services import (
    OVER_FETCH_FACTOR,
    DocumentHitGrouper,
)
from vectra.bounded_context.retrieval.domain.value_objects import (
    Embedding,
    EmbeddingProfile,
    SearchQuery,
)
from vectra.shared_kernel.application.handlers import IHandler
from vectra.utils import FrozenObject

from .check_collection_profile_handler import (
    CheckCollectionProfileHandler,
    CheckCollectionProfileQuery,
)


class SearchCollectionQuery(FrozenObject):
    """Search a collection.

    Attributes:
        collection: Collection name.
        text: Natural-language query.
        top_k: Documents to return.
        path_prefix: Only documents under this path prefix.
        min_score: Drop hits below this score (0..1).
    """

    collection: str
    text: str
    top_k: int = 5
    path_prefix: str | None = None
    min_score: float | None = None


class SearchHandler(IHandler[SearchCollectionQuery, SearchResultDTO]):
    """Embeds the query, over-fetches chunks and keeps the best chunk per document."""

    def __init__(
        self,
        *,
        profile_check: CheckCollectionProfileHandler,
        chunks: IChunkSearchReadRepository,
        embedder: IEmbedder,
        grouper: DocumentHitGrouper | None = None,
    ) -> None:
        self._profile_check: CheckCollectionProfileHandler = profile_check
        self._chunks: IChunkSearchReadRepository = chunks
        self._embedder: IEmbedder = embedder
        self._grouper: DocumentHitGrouper = grouper or DocumentHitGrouper()

    async def handle(self, action: SearchCollectionQuery) -> SearchResultDTO:
        """The matching documents.

        Raises:
            CollectionNotFoundError: There is no such collection.
            EmbeddingProfileMismatchError: The configured model differs from the collection's.
        """
        query = SearchQuery(
            text=action.text,
            top_k=action.top_k,
            path_prefix=action.path_prefix,
            min_score=action.min_score,
        )
        check: CollectionProfileCheckDTO = (
            await self._profile_check.handle(
                CheckCollectionProfileQuery(collection=action.collection)
            )
        ).collections[0]
        if not check.in_sync:
            self._embedder.profile.assert_matches(
                EmbeddingProfile(model_id=check.model_id, dimension=check.dimension),
                action.collection,
            )
        vector: Embedding = await self._embedder.embed_query(query.text)
        hits: list[ChunkHitDTO] = await self._chunks.search(
            action.collection, vector.values, query.path_prefix, query.top_k * OVER_FETCH_FACTOR
        )
        if query.min_score is not None:
            hits = [hit for hit in hits if hit.score >= query.min_score]
        return SearchResultDTO(
            collection=action.collection,
            query=query.text,
            hits=self._grouper.group(hits, query.top_k),
        )
