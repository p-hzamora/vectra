"""ChunkerResolver and DocumentHitGrouper."""

import pytest

from tests.support.retrieval_fakes import (
    FIXED_NOW,
    FakeChunker,
    FakeEmbedder,
    FakeRetrievalStore,
    FakeSource,
    no_sleep,
)
from vectra.bounded_context.retrieval.application.dtos import (
    ChunkHitDTO,
    FileFailureDTO,
    ManifestEntryDTO,
    SourceFileDTO,
)
from vectra.bounded_context.retrieval.application.services import (
    SNIPPET_CHARS,
    UNEXPECTED_CODE,
    ChunkerResolver,
    CollectionProvisioner,
    DocumentFingerprinter,
    DocumentHitGrouper,
    DocumentIndexer,
    DocumentRemover,
    RetryRunner,
)
from vectra.bounded_context.retrieval.domain.value_objects import (
    CollectionName,
    SourcePath,
    SourceRoot,
)
from vectra.exceptions import (
    ChunkingFailedError,
    EmbeddingDimensionMismatchError,
)

pytestmark = pytest.mark.unit


def test_resolver_picks_by_extension_case_insensitively() -> None:
    chunker = FakeChunker()
    resolver = ChunkerResolver([chunker])
    assert resolver.resolve(SourcePath(value="a/B.MD")) is chunker


def test_resolver_rejects_unknown_extensions() -> None:
    with pytest.raises(ChunkingFailedError) as raised:
        ChunkerResolver([FakeChunker()]).resolve(SourcePath(value="a.py"))
    assert raised.value.error_code == "RETRIEVAL_204_CHUNKING_FAILED"


def _hit(path: str, score: float, text: str = "t", chunk: str = "c") -> ChunkHitDTO:
    return ChunkHitDTO(chunk_id=chunk, path=path, heading_path=("H",), text=text, score=score)


def test_grouper_keeps_best_chunk_per_document_and_orders_by_score() -> None:
    hits = [
        _hit("a.md", 0.5, chunk="a1"),
        _hit("b.md", 0.9, chunk="b1"),
        _hit("a.md", 0.7, chunk="a2"),
        _hit("c.md", 0.7, chunk="c1"),
    ]
    grouped = DocumentHitGrouper().group(hits, top_k=2)
    assert [(item.path, item.chunk_id) for item in grouped] == [("b.md", "b1"), ("a.md", "a2")]


def test_grouper_truncates_long_snippets_only() -> None:
    long = DocumentHitGrouper().group([_hit("a.md", 1.0, text="x" * 1000)], top_k=1)[0]
    assert len(long.snippet) == SNIPPET_CHARS + 3
    assert long.snippet.endswith("...")
    short = DocumentHitGrouper().group([_hit("a.md", 1.0, text="short")], top_k=1)[0]
    assert short.snippet == "short"


HASH = "a" * 64
NAME = CollectionName(value="docs")
ROOT = SourceRoot(value="/data/docs")


def test_fingerprinter_fingerprints_handled_files_and_fails_the_rest() -> None:
    fingerprinter = DocumentFingerprinter(ChunkerResolver([FakeChunker("v7")]))
    files = [
        SourceFileDTO(path="a.md", content_hash=HASH, size=1),
        SourceFileDTO(path="b.txt", content_hash=HASH, size=1),
    ]
    fingerprints, failures = fingerprinter.scanned(files)
    assert [(item.path.value, item.chunker_version) for item in fingerprints] == [("a.md", "v7")]
    assert list(failures) == ["b.txt"]
    assert (failures["b.txt"].code, failures["b.txt"].attempts) == (
        "RETRIEVAL_204_CHUNKING_FAILED",
        0,
    )


def test_fingerprinter_maps_manifest_entries() -> None:
    fingerprinter = DocumentFingerprinter(ChunkerResolver([FakeChunker()]))
    entry = ManifestEntryDTO(path="a.md", content_hash=HASH, chunker_version="v1")
    (fingerprint,) = fingerprinter.indexed([entry])
    assert (fingerprint.path.value, fingerprint.content_hash.value) == ("a.md", HASH)
    assert fingerprint.chunker_version == "v1"


async def test_retry_runner_returns_the_result_of_a_working_operation() -> None:
    sleep, delays = no_sleep()

    async def operation() -> int:
        return 7

    runner = RetryRunner(max_retries=2, sleep=sleep)
    assert await runner.run(SourcePath(value="a.md"), operation) == 7
    assert delays == []


async def test_retry_runner_backs_off_then_reports_the_failure() -> None:
    sleep, delays = no_sleep()

    async def operation() -> int:
        raise RuntimeError("down")

    runner = RetryRunner(max_retries=2, backoff_seconds=0.1, sleep=sleep)
    outcome = await runner.run(SourcePath(value="a.md"), operation)
    assert outcome == FileFailureDTO(path="a.md", code=UNEXPECTED_CODE, message="down", attempts=3)
    assert delays == [0.1, 0.2]


async def test_retry_runner_keeps_the_code_of_a_project_error() -> None:
    sleep, _ = no_sleep()

    async def operation() -> None:
        raise ChunkingFailedError("bad", {"path": "a.md"})

    outcome = await RetryRunner(max_retries=0, sleep=sleep).run(SourcePath(value="a.md"), operation)
    assert isinstance(outcome, FileFailureDTO)
    assert (outcome.code, outcome.message, outcome.attempts) == (
        "RETRIEVAL_204_CHUNKING_FAILED",
        "bad",
        1,
    )


async def test_retry_runner_recovers_within_the_retries() -> None:
    sleep, delays = no_sleep()
    calls: list[int] = []

    async def operation() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("flaky")
        return "ok"

    assert (
        await RetryRunner(max_retries=2, sleep=sleep).run(SourcePath(value="a.md"), operation)
        == "ok"
    )
    assert len(delays) == 2


async def test_provisioner_creates_gets_and_drops_a_collection() -> None:
    store = FakeRetrievalStore()
    embedder = FakeEmbedder()
    provisioner = CollectionProvisioner(
        uow_factory=store.uow, embedder=embedder, clock=lambda: FIXED_NOW
    )
    assert await provisioner.get(NAME) is None
    await provisioner.create(NAME, ROOT)
    collection = await provisioner.get(NAME)
    assert collection is not None
    assert (collection.profile, collection.source_root, collection.created_at) == (
        embedder.profile,
        ROOT,
        FIXED_NOW,
    )
    await provisioner.drop(NAME)
    assert await provisioner.get(NAME) is None


def _indexer(
    store: FakeRetrievalStore, source: FakeSource, embedder: FakeEmbedder | None = None
) -> DocumentIndexer:
    return DocumentIndexer(
        uow_factory=store.uow,
        source=source,
        resolver=ChunkerResolver([FakeChunker()]),
        embedder=embedder or FakeEmbedder(),
    )


async def test_indexer_stores_chunks_and_reports_warnings() -> None:
    store = FakeRetrievalStore()
    indexer = _indexer(store, FakeSource({"a.md": "one\n\nWARN two"}))
    result = await indexer.index(NAME, ROOT, SourcePath(value="a.md"), HASH)
    assert result.chunks_written == 2
    assert result.warnings == ("a.md: fake warning",)
    assert len(store.chunks[("docs", "a.md")]) == 2
    assert store.documents[("docs", "a.md")].content_hash.value == HASH


async def test_indexer_replaces_a_document_that_was_already_indexed() -> None:
    store = FakeRetrievalStore()
    source = FakeSource({"a.md": "one\n\ntwo"})
    indexer = _indexer(store, source)
    await indexer.index(NAME, ROOT, SourcePath(value="a.md"), HASH)
    source.files["a.md"] = "only"
    await indexer.index(NAME, ROOT, SourcePath(value="a.md"), "b" * 64)
    assert len(store.chunks[("docs", "a.md")]) == 1
    assert store.documents[("docs", "a.md")].content_hash.value == "b" * 64


async def test_indexer_refuses_vectors_of_the_wrong_dimension_and_stores_nothing() -> None:
    class ShortEmbedder(FakeEmbedder):
        async def embed_documents(self, texts: object) -> list:  # type: ignore[type-arg, override]
            return []

    store = FakeRetrievalStore()
    indexer = _indexer(store, FakeSource({"a.md": "one"}), ShortEmbedder())
    with pytest.raises(EmbeddingDimensionMismatchError):
        await indexer.index(NAME, ROOT, SourcePath(value="a.md"), HASH)
    assert store.documents == {}


async def test_remover_deletes_the_document() -> None:
    store = FakeRetrievalStore()
    indexer = _indexer(store, FakeSource({"a.md": "one"}))
    await indexer.index(NAME, ROOT, SourcePath(value="a.md"), HASH)
    await DocumentRemover(uow_factory=store.uow).remove(NAME, SourcePath(value="a.md"))
    assert store.documents == {}
    assert store.chunks == {}
