"""Value objects validate themselves."""

import pytest

from vectra.bounded_context.retrieval.domain.value_objects import (
    ChunkId,
    CollectionName,
    ContentHash,
    Embedding,
    EmbeddingProfile,
    HeadingPath,
    SearchQuery,
    SourcePath,
    SourceRoot,
)
from vectra.exceptions import (
    EmbeddingDimensionMismatchError,
    InvalidCollectionNameError,
    InvalidRetrievalValueError,
    InvalidSearchQueryError,
    InvalidSourcePathError,
    SourceRootInvalidError,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("value", ["notes", "a1", "my-docs_2", "a" * 63])
def test_collection_name_accepts_valid_names(value: str) -> None:
    assert CollectionName(value=value).value == value


@pytest.mark.parametrize("value", ["", "Notes", "-a", "a b", "a/b", "a" * 64])
def test_collection_name_rejects_invalid_names(value: str) -> None:
    with pytest.raises(InvalidCollectionNameError) as raised:
        CollectionName(value=value)
    assert raised.value.error_code == "RETRIEVAL_001_INVALID_COLLECTION_NAME"


def test_source_path_is_relative_posix() -> None:
    assert SourcePath(value="a/b.md").value == "a/b.md"
    assert SourcePath(value="./a/b.md").value == "a/b.md"


@pytest.mark.parametrize("value", ["", "/abs.md", "../x.md", "a/../../x.md", "a\\b.md"])
def test_source_path_rejects_unsafe_paths(value: str) -> None:
    with pytest.raises(InvalidSourcePathError):
        SourcePath(value=value)


def test_hash_and_chunk_id_need_sha256_hex() -> None:
    ContentHash(value="a" * 64)
    ChunkId(value="b" * 64)
    with pytest.raises(InvalidRetrievalValueError):
        ContentHash(value="xyz")
    with pytest.raises(InvalidRetrievalValueError):
        ChunkId(value="A" * 64)


def test_heading_path_text() -> None:
    assert HeadingPath(parts=("A", "B")).as_text() == "A > B"
    assert HeadingPath().as_text() == ""


def test_embedding_profile_validates_and_fingerprints() -> None:
    profile = EmbeddingProfile(model_id="m", dimension=4)
    assert profile.fingerprint == "m:4"
    with pytest.raises(InvalidRetrievalValueError):
        EmbeddingProfile(model_id=" ", dimension=4)
    with pytest.raises(EmbeddingDimensionMismatchError):
        EmbeddingProfile(model_id="m", dimension=0)


def test_embedding_needs_values() -> None:
    assert Embedding(values=(1.0, 2.0)).dimension == 2
    with pytest.raises(EmbeddingDimensionMismatchError):
        Embedding(values=())


def test_search_query_defaults_and_limits() -> None:
    query = SearchQuery(text="hello")
    assert (query.top_k, query.path_prefix, query.min_score) == (5, None, None)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"text": "  "},
        {"text": "x", "top_k": 0},
        {"text": "x", "top_k": 101},
        {"text": "x", "path_prefix": "/abs"},
        {"text": "x", "path_prefix": "../x"},
        {"text": "x", "min_score": 1.5},
    ],
)
def test_search_query_rejects_bad_input(kwargs: dict[str, object]) -> None:
    with pytest.raises(InvalidSearchQueryError) as raised:
        SearchQuery.model_validate(kwargs)
    assert raised.value.next_steps


def test_search_query_accepts_prefix_and_min_score() -> None:
    query = SearchQuery(text="x", path_prefix="docs/", min_score=0.4)
    assert (query.path_prefix, query.min_score) == ("docs/", 0.4)


def test_source_root_must_be_absolute() -> None:
    assert SourceRoot(value="/a/b").value == "/a/b"
    with pytest.raises(SourceRootInvalidError):
        SourceRoot(value="a/b")


def test_profile_accepts_the_expected_vectors() -> None:
    profile = EmbeddingProfile(model_id="m", dimension=2)
    vectors = [Embedding(values=(1.0, 0.0)), Embedding(values=(0.0, 1.0))]
    profile.assert_embeddings(vectors, 2, "a.md")


@pytest.mark.parametrize(
    "vectors",
    [[Embedding(values=(1.0, 0.0))], [Embedding(values=(1.0,)), Embedding(values=(1.0, 0.0))]],
    ids=["wrong-count", "wrong-dimension"],
)
def test_profile_rejects_unexpected_vectors(vectors: list[Embedding]) -> None:
    profile = EmbeddingProfile(model_id="m", dimension=2)
    with pytest.raises(EmbeddingDimensionMismatchError) as raised:
        profile.assert_embeddings(vectors, 2, "a.md")
    assert raised.value.metadata == {"path": "a.md"}


def test_empty_model_id_error_tells_how_to_fix_it() -> None:
    with pytest.raises(InvalidRetrievalValueError) as raised:
        EmbeddingProfile(model_id=" ", dimension=4)
    assert raised.value.next_steps
