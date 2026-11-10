"""ChunkerResolver and DocumentHitGrouper."""

import pytest

from tests.support.retrieval_fakes import FakeChunker
from vectra.bounded_context.retrieval.application.dtos import ChunkHitDTO
from vectra.bounded_context.retrieval.application.services import (
    SNIPPET_CHARS,
    ChunkerResolver,
    DocumentHitGrouper,
)
from vectra.bounded_context.retrieval.domain.value_objects import SourcePath
from vectra.exceptions import ChunkingFailedError

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
