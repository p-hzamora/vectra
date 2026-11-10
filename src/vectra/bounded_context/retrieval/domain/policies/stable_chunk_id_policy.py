"""Derives chunk ids that survive edits elsewhere in the document."""

import hashlib
from collections import Counter
from collections.abc import Sequence

from vectra.bounded_context.retrieval.domain.value_objects import (
    ChunkContent,
    ChunkId,
    CollectionName,
    SourcePath,
)


class StableChunkIdPolicy:
    """`sha256(collection|path|heading_path|sha256(text)[:16])`.

    A counter is appended only to the second and later chunks with identical heading path
    and text, so adding a duplicate never changes the id of an existing chunk.
    """

    def assign(
        self, collection: CollectionName, path: SourcePath, chunks: Sequence[ChunkContent]
    ) -> tuple[ChunkId, ...]:
        """One id per chunk, in order."""
        seen: Counter[str] = Counter()
        ids: list[ChunkId] = []
        for chunk in chunks:
            text_digest: str = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()[:16]
            key: str = (
                f"{collection.value}|{path.value}|{chunk.heading_path.as_text()}|{text_digest}"
            )
            occurrence: int = seen[key]
            seen[key] += 1
            material: str = key if occurrence == 0 else f"{key}|{occurrence}"
            ids.append(ChunkId(value=hashlib.sha256(material.encode("utf-8")).hexdigest()))
        return tuple(ids)
