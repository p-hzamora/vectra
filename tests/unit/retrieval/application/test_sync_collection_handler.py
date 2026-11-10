"""SyncCollectionHandler with in-memory fakes."""

import pytest

from tests.support.retrieval_fakes import (
    FIXED_NOW,
    FakeChunker,
    FakeEmbedder,
    FakeRetrievalStore,
    FakeSource,
    no_sleep,
)
from vectra.bounded_context.retrieval.application.dtos import SyncResultDTO
from vectra.bounded_context.retrieval.application.handlers.commands import (
    SyncCollectionCommand,
    SyncCollectionHandler,
)
from vectra.bounded_context.retrieval.application.services import ChunkerResolver
from vectra.exceptions import (
    EmbeddingProfileMismatchError,
    MassDeleteRefusedError,
    SourceRootInvalidError,
)

pytestmark = pytest.mark.unit

ROOT = "/data/docs"


class Rig:
    def __init__(self, max_retries: int = 2) -> None:
        self.store = FakeRetrievalStore()
        self.source = FakeSource({"a.md": "alpha one\n\nalpha two", "b.md": "beta"})
        self.embedder = FakeEmbedder()
        self.chunker = FakeChunker()
        self.sleep, self.delays = no_sleep()
        self.max_retries = max_retries

    def handler(self) -> SyncCollectionHandler:
        return SyncCollectionHandler(
            uow_factory=self.store.uow,
            manifest=self.store.manifest(),
            source=self.source,
            resolver=ChunkerResolver([self.chunker]),
            embedder=self.embedder,
            max_retries=self.max_retries,
            backoff_seconds=0.1,
            sleep=self.sleep,
            clock=lambda: FIXED_NOW,
        )

    async def sync(self, **options: object) -> SyncResultDTO:
        command = SyncCollectionCommand.model_validate(
            {"collection": "docs", "root": ROOT, **options}
        )
        return await self.handler().handle(command)


async def test_first_sync_creates_the_collection_and_indexes_everything() -> None:
    rig = Rig()
    result = await rig.sync()
    assert (result.created, result.dry_run) == (True, False)
    assert result.added == ("a.md", "b.md")
    assert result.chunks_written == 3
    collection = rig.store.collections["docs"]
    assert collection.source_root.value == ROOT
    assert collection.created_at == FIXED_NOW
    assert collection.profile == rig.embedder.profile
    assert len(rig.store.chunks[("docs", "a.md")]) == 2


async def test_second_sync_changes_nothing() -> None:
    rig = Rig()
    await rig.sync()
    rig.embedder.calls.clear()
    result = await rig.sync()
    assert (result.added, result.updated, result.deleted) == ((), (), ())
    assert (result.unchanged, result.created, result.chunks_written) == (2, False, 0)
    assert rig.embedder.calls == []


async def test_changed_content_is_reindexed_and_stale_chunks_dropped() -> None:
    rig = Rig()
    await rig.sync()
    rig.source.files["a.md"] = "alpha one"
    result = await rig.sync()
    assert result.updated == ("a.md",)
    document = rig.store.documents[("docs", "a.md")]
    assert len(document.chunk_ids) == 1
    assert len(rig.store.chunks[("docs", "a.md")]) == 1


async def test_new_chunker_version_reindexes_unchanged_files() -> None:
    rig = Rig()
    await rig.sync()
    rig.chunker.version = "fake-2"
    result = await rig.sync()
    assert result.updated == ("a.md", "b.md")


async def test_rename_is_delete_plus_add() -> None:
    rig = Rig()
    await rig.sync()
    rig.source.files["c.md"] = rig.source.files.pop("b.md")
    result = await rig.sync()
    assert (result.added, result.deleted) == (("c.md",), ("b.md",))
    assert ("docs", "b.md") not in rig.store.documents


async def test_dry_run_reports_the_plan_and_writes_nothing() -> None:
    rig = Rig()
    result = await rig.sync(dry_run=True)
    assert (result.dry_run, result.created, result.added) == (True, True, ("a.md", "b.md"))
    assert rig.store.collections == {}
    assert rig.store.documents == {}
    assert rig.embedder.calls == []


async def test_dry_run_on_existing_collection_plans_updates() -> None:
    rig = Rig()
    await rig.sync()
    rig.source.files["a.md"] = "changed"
    result = await rig.sync(dry_run=True)
    assert (result.created, result.updated, result.unchanged) == (False, ("a.md",), 1)


async def test_other_root_is_refused_with_102() -> None:
    rig = Rig()
    await rig.sync()
    with pytest.raises(SourceRootInvalidError) as raised:
        await rig.sync(root="/somewhere/else")
    assert raised.value.error_code == "RETRIEVAL_102_SOURCE_ROOT_INVALID"


async def test_other_embedding_profile_is_refused_with_003() -> None:
    rig = Rig()
    await rig.sync()
    rig.embedder = FakeEmbedder(model_id="another-model")
    with pytest.raises(EmbeddingProfileMismatchError) as raised:
        await rig.sync()
    assert raised.value.error_code == "RETRIEVAL_003_INDEX_PROFILE_MISMATCH"


async def test_missing_root_aborts_before_touching_the_store() -> None:
    rig = Rig()
    await rig.sync()
    rig.source.missing_root = True
    with pytest.raises(SourceRootInvalidError):
        await rig.sync()
    assert len(rig.store.documents) == 2


async def test_deleting_more_than_half_requires_the_flag() -> None:
    rig = Rig()
    await rig.sync()
    rig.source.files.clear()
    with pytest.raises(MassDeleteRefusedError) as raised:
        await rig.sync()
    assert raised.value.error_code == "RETRIEVAL_103_MASS_DELETE_REFUSED"
    assert len(rig.store.documents) == 2
    with pytest.raises(MassDeleteRefusedError):
        await rig.sync(dry_run=True)
    result = await rig.sync(allow_mass_delete=True)
    assert result.deleted == ("a.md", "b.md")
    assert rig.store.documents == {}


async def test_deleting_exactly_half_is_allowed() -> None:
    rig = Rig()
    await rig.sync()
    del rig.source.files["b.md"]
    result = await rig.sync()
    assert result.deleted == ("b.md",)


async def test_failed_file_is_retried_then_reported_with_attempts_and_others_continue() -> None:
    rig = Rig(max_retries=2)
    rig.embedder.failures["beta"] = 99
    result = await rig.sync()
    assert result.added == ("a.md",)
    assert len(result.failed) == 1
    failure = result.failed[0]
    assert (failure.path, failure.attempts, failure.code) == (
        "b.md",
        3,
        "RETRIEVAL_000_UNEXPECTED",
    )
    assert "boom" in failure.message
    assert rig.delays == [0.1, 0.2]
    assert ("docs", "b.md") not in rig.store.documents


async def test_a_file_that_recovers_within_the_retries_succeeds() -> None:
    rig = Rig(max_retries=2)
    rig.store.save_failures["a.md"] = 2
    result = await rig.sync()
    assert result.failed == ()
    assert result.added == ("a.md", "b.md")


async def test_zero_retries_means_one_attempt() -> None:
    rig = Rig(max_retries=0)
    rig.embedder.failures["beta"] = 1
    result = await rig.sync()
    assert result.failed[0].attempts == 1
    assert rig.delays == []


async def test_failed_file_is_picked_up_by_the_next_sync() -> None:
    rig = Rig(max_retries=0)
    rig.embedder.failures["beta"] = 1
    await rig.sync()
    result = await rig.sync()
    assert (result.added, result.failed) == (("b.md",), ())


async def test_failed_deletion_is_reported() -> None:
    rig = Rig(max_retries=0)
    await rig.sync()
    del rig.source.files["b.md"]
    rig.store.delete_failures.add("b.md")
    result = await rig.sync()
    assert result.deleted == ()
    assert [(item.path, item.attempts) for item in result.failed] == [("b.md", 1)]


async def test_unsupported_extension_is_a_failure_without_attempts() -> None:
    rig = Rig()
    rig.source.files["notes.txt"] = "plain"
    result = await rig.sync(include=["**/*"])
    assert [(item.path, item.code, item.attempts) for item in result.failed] == [
        ("notes.txt", "RETRIEVAL_204_CHUNKING_FAILED", 0)
    ]
    assert result.added == ("a.md", "b.md")


async def test_chunker_warnings_surface_in_the_result() -> None:
    rig = Rig()
    rig.source.files["a.md"] = "WARN me"
    result = await rig.sync()
    assert result.warnings == ("a.md: fake warning",)


async def test_empty_document_is_indexed_without_chunks() -> None:
    rig = Rig()
    rig.source.files = {"empty.md": ""}
    result = await rig.sync()
    assert result.added == ("empty.md",)
    assert result.chunks_written == 0
    assert rig.store.documents[("docs", "empty.md")].chunk_ids == ()


async def test_embedder_returning_the_wrong_dimension_fails_the_file() -> None:
    rig = Rig(max_retries=0)

    class Wrong(FakeEmbedder):
        async def embed_documents(self, texts):  # type: ignore[no-untyped-def]
            return [await self.embed_query("x")] * (len(texts) + 1)

    rig.embedder = Wrong()
    result = await rig.sync()
    assert {item.code for item in result.failed} == {"RETRIEVAL_005_EMBEDDING_DIMENSION_MISMATCH"}


async def test_rebuild_recreates_the_collection_with_new_profile_and_root() -> None:
    rig = Rig()
    await rig.sync()
    rig.embedder = FakeEmbedder(model_id="another-model")
    result = await rig.sync(rebuild=True, root="/new/root")
    assert (result.created, result.added, result.unchanged) == (True, ("a.md", "b.md"), 0)
    collection = rig.store.collections["docs"]
    assert collection.profile.model_id == "another-model"
    assert collection.source_root.value == "/new/root"
    assert len(rig.store.documents) == 2


async def test_rebuild_bypasses_the_mass_delete_guard() -> None:
    rig = Rig()
    await rig.sync()
    rig.source.files = {"only.md": "x"}
    result = await rig.sync(rebuild=True)
    assert result.added == ("only.md",)
    assert result.deleted == ()
    assert list(rig.store.documents) == [("docs", "only.md")]


async def test_rebuild_dry_run_drops_nothing() -> None:
    rig = Rig()
    await rig.sync()
    result = await rig.sync(rebuild=True, dry_run=True)
    assert (result.dry_run, result.created, result.added) == (True, True, ("a.md", "b.md"))
    assert len(rig.store.documents) == 2
    assert rig.store.collections["docs"].profile.model_id == "fake-model"


async def test_rebuild_of_a_new_collection_just_creates_it() -> None:
    result = await Rig().sync(rebuild=True)
    assert (result.created, result.added) == (True, ("a.md", "b.md"))
