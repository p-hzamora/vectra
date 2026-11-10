"""Sync planning and stable chunk ids."""

import hashlib

import pytest

from vectra.bounded_context.retrieval.domain.policies import (
    StableChunkIdPolicy,
    SyncPlanningPolicy,
)
from vectra.bounded_context.retrieval.domain.value_objects import (
    ChunkContent,
    CollectionName,
    ContentHash,
    DocumentFingerprint,
    HeadingPath,
    SourcePath,
)

pytestmark = pytest.mark.unit


def _fp(path: str, content: str = "a", version: str = "v1") -> DocumentFingerprint:
    return DocumentFingerprint(
        path=SourcePath(value=path),
        content_hash=ContentHash(value=hashlib.sha256(content.encode()).hexdigest()),
        chunker_version=version,
    )


def _values(paths: tuple[SourcePath, ...]) -> list[str]:
    return [path.value for path in paths]


def test_plan_classifies_every_document() -> None:
    scanned = [_fp("new.md"), _fp("same.md"), _fp("changed.md", "b"), _fp("rechunk.md")]
    indexed = [
        _fp("same.md"),
        _fp("changed.md", "a"),
        _fp("rechunk.md", version="v0"),
        _fp("gone.md"),
    ]
    plan = SyncPlanningPolicy().plan(scanned, indexed)
    assert _values(plan.add) == ["new.md"]
    assert _values(plan.update) == ["changed.md", "rechunk.md"]
    assert _values(plan.delete) == ["gone.md"]
    assert _values(plan.unchanged) == ["same.md"]


def test_rename_is_delete_plus_add() -> None:
    plan = SyncPlanningPolicy().plan([_fp("b.md")], [_fp("a.md")])
    assert (_values(plan.add), _values(plan.delete)) == (["b.md"], ["a.md"])


def test_plan_of_nothing_is_empty() -> None:
    plan = SyncPlanningPolicy().plan([], [])
    assert plan.add == plan.update == plan.delete == plan.unchanged == ()


def _chunk(text: str, *headings: str) -> ChunkContent:
    return ChunkContent(heading_path=HeadingPath(parts=headings), text=text)


def test_chunk_ids_are_deterministic_and_scoped() -> None:
    policy = StableChunkIdPolicy()
    path = SourcePath(value="a.md")
    first = policy.assign(CollectionName(value="c"), path, [_chunk("x", "H")])
    again = policy.assign(CollectionName(value="c"), path, [_chunk("x", "H")])
    other_collection = policy.assign(CollectionName(value="d"), path, [_chunk("x", "H")])
    other_path = policy.assign(
        CollectionName(value="c"), SourcePath(value="b.md"), [_chunk("x", "H")]
    )
    other_heading = policy.assign(CollectionName(value="c"), path, [_chunk("x", "G")])
    assert first == again
    assert len({first[0], other_collection[0], other_path[0], other_heading[0]}) == 4


def test_identical_heading_and_text_get_an_occurrence_counter() -> None:
    policy = StableChunkIdPolicy()
    name, path = CollectionName(value="c"), SourcePath(value="a.md")
    ids = policy.assign(name, path, [_chunk("same", "H"), _chunk("same", "H"), _chunk("same", "H")])
    assert len(set(ids)) == 3


def test_adding_a_duplicate_keeps_the_first_id_stable() -> None:
    policy = StableChunkIdPolicy()
    name, path = CollectionName(value="c"), SourcePath(value="a.md")
    before = policy.assign(name, path, [_chunk("same", "H")])
    after = policy.assign(name, path, [_chunk("same", "H"), _chunk("same", "H")])
    assert after[0] == before[0]
    assert after[1] != before[0]


def test_editing_another_chunk_does_not_change_ids() -> None:
    policy = StableChunkIdPolicy()
    name, path = CollectionName(value="c"), SourcePath(value="a.md")
    before = policy.assign(name, path, [_chunk("one", "A"), _chunk("two", "B")])
    after = policy.assign(name, path, [_chunk("ONE edited", "A"), _chunk("two", "B")])
    assert after[1] == before[1]
    assert after[0] != before[0]
