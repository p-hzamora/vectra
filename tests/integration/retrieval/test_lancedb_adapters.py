"""LanceDB adapters in a temporary folder, through the real handlers and a fake embedder."""

import hashlib
from pathlib import Path

import pytest

from tests.support.retrieval_fakes import FIXED_NOW, FakeEmbedder, FakeSource, no_sleep
from vectra.bounded_context.retrieval.application.handlers.commands import (
    DropCollectionCommand,
    DropCollectionHandler,
    SyncCollectionCommand,
    SyncCollectionHandler,
)
from vectra.bounded_context.retrieval.application.handlers.queries import (
    ListCollectionsHandler,
    ListCollectionsQuery,
    SearchCollectionHandler,
    SearchCollectionQuery,
)
from vectra.bounded_context.retrieval.application.services import ChunkerResolver
from vectra.bounded_context.retrieval.domain.entities import IndexedDocument
from vectra.bounded_context.retrieval.domain.value_objects import (
    ChunkId,
    CollectionName,
    ContentHash,
    SourcePath,
)
from vectra.bounded_context.retrieval.infrastructure.outbound.chunking import (
    MarkdownChunkerAdapter,
)
from vectra.bounded_context.retrieval.infrastructure.outbound.vector_store import (
    LanceDbChunkSearchReadRepositoryAdapter,
    LanceDbCollectionReadRepositoryAdapter,
    LanceDbCollectionRepositoryAdapter,
    LanceDbIndexedDocumentRepositoryAdapter,
    LanceDbManifestReadRepositoryAdapter,
    LanceDbRetrievalUnitOfWorkAdapter,
    LanceDbStore,
)
from vectra.exceptions import VectorStoreError

pytestmark = pytest.mark.integration

FILES = {
    "cats.md": "# Cats\nfelines purr and hunt mice at night",
    "dogs.md": "# Dogs\ncanines bark and fetch sticks outdoors",
    "docs/guide.md": "# Guide\nhow to install the software and run it",
}


class Stack:
    def __init__(self, tmp_path: Path, files: dict[str, str] | None = None) -> None:
        self.store = LanceDbStore(tmp_path / "index")
        self.source = FakeSource(dict(FILES if files is None else files))
        self.embedder = FakeEmbedder()
        self.sleep, _ = no_sleep()
        self.collections = LanceDbCollectionReadRepositoryAdapter(self.store)

    def uow(self) -> LanceDbRetrievalUnitOfWorkAdapter:
        return LanceDbRetrievalUnitOfWorkAdapter(self.store)

    def sync(self) -> SyncCollectionHandler:
        return SyncCollectionHandler(
            uow_factory=self.uow,
            manifest=LanceDbManifestReadRepositoryAdapter(self.store),
            source=self.source,
            resolver=ChunkerResolver([MarkdownChunkerAdapter()]),
            embedder=self.embedder,
            max_retries=0,
            sleep=self.sleep,
            clock=lambda: FIXED_NOW,
        )

    def search(self) -> SearchCollectionHandler:
        return SearchCollectionHandler(
            collections=self.collections,
            chunks=LanceDbChunkSearchReadRepositoryAdapter(self.store),
            embedder=self.embedder,
        )


def _command(**options: object) -> SyncCollectionCommand:
    return SyncCollectionCommand.model_validate({"collection": "docs", "root": "/r", **options})


async def test_sync_then_search_ranks_the_relevant_document_first(tmp_path: Path) -> None:
    stack = Stack(tmp_path)
    result = await stack.sync().handle(_command())
    assert result.added == ("cats.md", "docs/guide.md", "dogs.md")
    found = await stack.search().handle(
        SearchCollectionQuery(collection="docs", text="felines purr and hunt mice", top_k=3)
    )
    assert found.hits[0].path == "cats.md"
    assert found.hits[0].heading_path == ("Cats",)
    assert 0.0 <= found.hits[-1].score <= found.hits[0].score <= 1.0
    assert len(found.hits) == 3


async def test_search_respects_path_prefix_with_quotes_safely(tmp_path: Path) -> None:
    stack = Stack(tmp_path)
    await stack.sync().handle(_command())
    found = await stack.search().handle(
        SearchCollectionQuery(collection="docs", text="install software", path_prefix="docs/")
    )
    assert [hit.path for hit in found.hits] == ["docs/guide.md"]
    none = await stack.search().handle(
        SearchCollectionQuery(collection="docs", text="x", path_prefix="it's/")
    )
    assert none.hits == ()


async def test_state_survives_a_new_store_instance(tmp_path: Path) -> None:
    await Stack(tmp_path).sync().handle(_command())
    again = await Stack(tmp_path).sync().handle(_command())
    assert (again.added, again.updated, again.deleted, again.unchanged) == ((), (), (), 3)


async def test_update_replaces_chunks_and_delete_removes_them(tmp_path: Path) -> None:
    stack = Stack(tmp_path)
    await stack.sync().handle(_command())
    stack.source.files["cats.md"] = "# Cats\nnow only about aquariums and fish"
    del stack.source.files["dogs.md"]
    result = await stack.sync().handle(_command())
    assert (result.updated, result.deleted) == (("cats.md",), ("dogs.md",))
    listing = await ListCollectionsHandler(read_repository=stack.collections).handle(
        ListCollectionsQuery()
    )
    status = listing.collections[0]
    assert (status.document_count, status.chunk_count) == (2, 2)
    found = await stack.search().handle(SearchCollectionQuery(collection="docs", text="felines"))
    assert all("felines" not in hit.snippet for hit in found.hits)


async def test_list_reports_profile_root_and_creation(tmp_path: Path) -> None:
    stack = Stack(tmp_path)
    assert (await stack.collections.list_collections()) == []
    assert await stack.collections.get_status("docs") is None
    await stack.sync().handle(_command())
    status = await stack.collections.get_status("docs")
    assert status is not None
    assert (status.model_id, status.dimension, status.source_root) == ("fake-model", 16, "/r")
    assert status.created_at == FIXED_NOW
    assert [item.name for item in await stack.collections.list_collections()] == ["docs"]


async def test_drop_removes_everything(tmp_path: Path) -> None:
    stack = Stack(tmp_path)
    await stack.sync().handle(_command())
    await stack.sync().handle(_command(collection="other"))
    dropped = await DropCollectionHandler(
        uow_factory=stack.uow, read_repository=stack.collections
    ).handle(DropCollectionCommand(name="docs"))
    assert (dropped.documents, dropped.chunks) == (3, 3)
    assert [item.name for item in await stack.collections.list_collections()] == ["other"]
    other = await stack.collections.get_status("other")
    assert other is not None and other.document_count == 3
    manifest = LanceDbManifestReadRepositoryAdapter(stack.store)
    assert [entry async for entry in manifest.stream("docs")] == []


async def test_search_in_missing_table_returns_nothing(tmp_path: Path) -> None:
    stack = Stack(tmp_path)
    hits = await LanceDbChunkSearchReadRepositoryAdapter(stack.store).search("nope", [0.1], None, 5)
    assert hits == []


async def test_repository_save_and_get_roundtrip(tmp_path: Path) -> None:
    stack = Stack(tmp_path)
    await stack.sync().handle(_command())
    repository = LanceDbIndexedDocumentRepositoryAdapter(stack.store)
    name, path = CollectionName(value="docs"), SourcePath(value="cats.md")
    document = await repository.get(name, path)
    assert document is not None
    assert document.content_hash.value == hashlib.sha256(FILES["cats.md"].encode()).hexdigest()
    assert len(document.chunk_ids) == 1
    assert await repository.get(name, SourcePath(value="missing.md")) is None
    assert (
        await LanceDbCollectionRepositoryAdapter(stack.store).get(CollectionName(value="zzz"))
        is None
    )


async def test_manifest_is_written_last_so_a_failed_store_write_is_retried(tmp_path: Path) -> None:
    stack = Stack(tmp_path)
    await stack.sync().handle(_command())
    repository = LanceDbIndexedDocumentRepositoryAdapter(stack.store)
    orphan = IndexedDocument(
        collection=CollectionName(value="ghost"),
        path=SourcePath(value="a.md"),
        content_hash=ContentHash(value="a" * 64),
        chunker_version="v",
        chunk_ids=(ChunkId(value="b" * 64),),
    )
    with pytest.raises(VectorStoreError):
        await repository.save(orphan, [])
    assert await repository.get(CollectionName(value="ghost"), SourcePath(value="a.md")) is None


async def test_unit_of_work_exposes_repositories_and_commits(tmp_path: Path) -> None:
    uow = Stack(tmp_path).uow()
    async with uow as scope:
        await scope.commit()
        assert scope.collections is not None and scope.documents is not None
    assert uow.committed
