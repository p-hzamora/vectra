"""Collection and IndexedDocument behaviour."""

from datetime import UTC, datetime

import pytest

from vectra.bounded_context.retrieval.domain.entities import Collection, IndexedDocument
from vectra.bounded_context.retrieval.domain.value_objects import (
    ChunkId,
    CollectionName,
    ContentHash,
    EmbeddingProfile,
    SourcePath,
    SourceRoot,
)
from vectra.exceptions import EmbeddingProfileMismatchError, SourceRootMismatchError

pytestmark = pytest.mark.unit


def _collection() -> Collection:
    return Collection(
        name=CollectionName(value="docs"),
        profile=EmbeddingProfile(model_id="m", dimension=4),
        source_root=SourceRoot(value="/data/docs"),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_compatible_profile_passes() -> None:
    _collection().assert_compatible(EmbeddingProfile(model_id="m", dimension=4))


@pytest.mark.parametrize("profile", [("other", 4), ("m", 8)])
def test_other_model_or_dimension_is_rejected(profile: tuple[str, int]) -> None:
    with pytest.raises(EmbeddingProfileMismatchError) as raised:
        _collection().assert_compatible(EmbeddingProfile(model_id=profile[0], dimension=profile[1]))
    assert raised.value.error_code == "RETRIEVAL_003_EMBEDDING_PROFILE_MISMATCH"


def test_other_root_is_rejected() -> None:
    collection = _collection()
    collection.assert_same_root(SourceRoot(value="/data/docs"))
    with pytest.raises(SourceRootMismatchError) as raised:
        collection.assert_same_root(SourceRoot(value="/elsewhere"))
    assert raised.value.error_code == "RETRIEVAL_102_SOURCE_ROOT_MISMATCH"


def test_collections_are_equal_by_name() -> None:
    assert _collection() == _collection()
    assert hash(_collection()) == hash(_collection())
    assert _collection() != object()


def _id(char: str) -> ChunkId:
    return ChunkId(value=char * 64)


def _document() -> IndexedDocument:
    return IndexedDocument(
        collection=CollectionName(value="docs"),
        path=SourcePath(value="a.md"),
        content_hash=ContentHash(value="a" * 64),
        chunker_version="v1",
        chunk_ids=(_id("1"), _id("2")),
    )


def test_reindex_returns_stale_ids_and_updates_state() -> None:
    document = _document()
    stale = document.reindex(ContentHash(value="b" * 64), "v2", [_id("2"), _id("3")])
    assert stale == (_id("1"),)
    assert document.chunk_ids == (_id("2"), _id("3"))
    assert (document.content_hash.value, document.chunker_version) == ("b" * 64, "v2")


def test_documents_are_equal_by_collection_and_path() -> None:
    assert _document() == _document()
    assert hash(_document()) == hash(_document())
    assert _document() != object()
