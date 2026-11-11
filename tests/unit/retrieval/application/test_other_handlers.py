"""Drop, list and search handlers."""

import pytest

from tests.support.retrieval_fakes import (
    FakeChunker,
    FakeChunkSearchReadRepository,
    FakeCollectionReadRepository,
    FakeEmbedder,
    FakeRetrievalStore,
    FakeSource,
    build_sync_handler,
)
from vectra.bounded_context.retrieval.application.dtos import ChunkHitDTO
from vectra.bounded_context.retrieval.application.handlers.commands import (
    DropCollectionCommand,
    DropCollectionHandler,
    SyncCollectionCommand,
)
from vectra.bounded_context.retrieval.application.handlers.queries import (
    CheckCollectionProfileHandler,
    CheckCollectionProfileQuery,
    ListCollectionsHandler,
    ListCollectionsQuery,
    SearchCollectionQuery,
    SearchHandler,
)
from vectra.exceptions import (
    CollectionNotFoundError,
    EmbeddingProfileMismatchError,
    InvalidSearchQueryError,
)

pytestmark = pytest.mark.unit


async def _seeded_store() -> FakeRetrievalStore:
    store = FakeRetrievalStore()
    await build_sync_handler(
        uow_factory=store.uow,
        manifest=store.manifest(),
        source=FakeSource({"a.md": "alpha\n\nbeta"}),
        embedder=FakeEmbedder(),
        chunker=FakeChunker(),
    ).handle(SyncCollectionCommand(collection="docs", root="/r"))
    return store


async def test_list_returns_collections_sorted() -> None:
    store = await _seeded_store()
    result = await ListCollectionsHandler(
        read_repository=FakeCollectionReadRepository(store)
    ).handle(ListCollectionsQuery())
    assert [(item.name, item.document_count, item.chunk_count) for item in result.collections] == [
        ("docs", 1, 2)
    ]


async def test_drop_removes_the_collection_and_reports_what_it_held() -> None:
    store = await _seeded_store()
    handler = DropCollectionHandler(
        uow_factory=store.uow, read_repository=FakeCollectionReadRepository(store)
    )
    result = await handler.handle(DropCollectionCommand(name="docs"))
    assert (result.name, result.documents, result.chunks) == ("docs", 1, 2)
    assert store.collections == {}
    with pytest.raises(CollectionNotFoundError) as raised:
        await handler.handle(DropCollectionCommand(name="docs"))
    assert raised.value.error_code == "RETRIEVAL_101_COLLECTION_NOT_FOUND"


def _hit(path: str, score: float, chunk: str) -> ChunkHitDTO:
    return ChunkHitDTO(chunk_id=chunk, path=path, heading_path=(), text="body", score=score)


async def _search_handler(store: FakeRetrievalStore, embedder: FakeEmbedder) -> SearchHandler:
    return SearchHandler(
        profile_check=CheckCollectionProfileHandler(
            read_repository=FakeCollectionReadRepository(store), embedder=embedder
        ),
        chunks=FakeChunkSearchReadRepository(store),
        embedder=embedder,
    )


async def test_search_overfetches_groups_and_filters_by_min_score() -> None:
    store = await _seeded_store()
    store.hits = [_hit("a.md", 0.9, "1"), _hit("a.md", 0.8, "2"), _hit("b.md", 0.2, "3")]
    handler = await _search_handler(store, FakeEmbedder())
    result = await handler.handle(
        SearchCollectionQuery(collection="docs", text="alpha", top_k=2, path_prefix="x/")
    )
    assert store.last_search == ("docs", "x/", 8)
    assert [(hit.path, hit.chunk_id) for hit in result.hits] == [("a.md", "1"), ("b.md", "3")]
    filtered = await handler.handle(
        SearchCollectionQuery(collection="docs", text="alpha", min_score=0.5)
    )
    assert [hit.path for hit in filtered.hits] == ["a.md"]


async def test_search_unknown_collection_is_101() -> None:
    handler = await _search_handler(FakeRetrievalStore(), FakeEmbedder())
    with pytest.raises(CollectionNotFoundError):
        await handler.handle(SearchCollectionQuery(collection="nope", text="x"))


async def test_search_asserts_profile_compatibility() -> None:
    store = await _seeded_store()
    handler = await _search_handler(store, FakeEmbedder(model_id="other"))
    with pytest.raises(EmbeddingProfileMismatchError):
        await handler.handle(SearchCollectionQuery(collection="docs", text="x"))


async def test_search_validates_the_query() -> None:
    handler = await _search_handler(await _seeded_store(), FakeEmbedder())
    with pytest.raises(InvalidSearchQueryError):
        await handler.handle(SearchCollectionQuery(collection="docs", text="x", top_k=0))


async def test_check_reports_each_collection_against_the_configured_model() -> None:
    store = await _seeded_store()
    repository = FakeCollectionReadRepository(store)
    synced = await CheckCollectionProfileHandler(
        read_repository=repository, embedder=FakeEmbedder()
    ).handle(CheckCollectionProfileQuery())
    assert synced.in_sync
    drifted = await CheckCollectionProfileHandler(
        read_repository=repository, embedder=FakeEmbedder(model_id="other")
    ).handle(CheckCollectionProfileQuery(collection="docs"))
    assert not drifted.in_sync
    assert drifted.collections[0].configured_model_id == "other"


async def test_check_unknown_collection_is_101() -> None:
    handler = CheckCollectionProfileHandler(
        read_repository=FakeCollectionReadRepository(FakeRetrievalStore()), embedder=FakeEmbedder()
    )
    with pytest.raises(CollectionNotFoundError):
        await handler.handle(CheckCollectionProfileQuery(collection="nope"))
