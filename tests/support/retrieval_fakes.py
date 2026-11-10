"""In-memory and deterministic stand-ins for the retrieval ports."""

import hashlib
import math
import re
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from datetime import UTC, datetime
from types import TracebackType
from typing import Self

from vectra.bounded_context.retrieval.application.dtos import (
    ChunkHitDTO,
    CollectionStatusDTO,
    ManifestEntryDTO,
    SourceFileDTO,
)
from vectra.bounded_context.retrieval.application.ports.chunking import IChunker
from vectra.bounded_context.retrieval.application.ports.embedding import IEmbedder
from vectra.bounded_context.retrieval.application.ports.read_repositories import (
    IChunkSearchReadRepository,
    ICollectionReadRepository,
    IManifestReadRepository,
)
from vectra.bounded_context.retrieval.application.ports.source import IDocumentSource
from vectra.bounded_context.retrieval.application.ports.uow import IRetrievalUnitOfWork
from vectra.bounded_context.retrieval.domain.entities import Collection, IndexedDocument
from vectra.bounded_context.retrieval.domain.repositories import (
    ICollectionRepository,
    IIndexedDocumentRepository,
)
from vectra.bounded_context.retrieval.domain.value_objects import (
    ChunkContent,
    ChunkedDocument,
    CollectionName,
    EmbeddedChunk,
    Embedding,
    EmbeddingProfile,
    HeadingPath,
    SourcePath,
)

DIMENSION: int = 16


class FakeEmbedder(IEmbedder):
    """Bag-of-words hashing into `DIMENSION` buckets, normalized: texts sharing words are close."""

    def __init__(self, model_id: str = "fake-model", dimension: int = DIMENSION) -> None:
        self._profile = EmbeddingProfile(model_id=model_id, dimension=dimension)
        self.failures: dict[str, int] = {}
        self.calls: list[list[str]] = []

    @property
    def profile(self) -> EmbeddingProfile:
        return self._profile

    def _vector(self, text: str) -> Embedding:
        values: list[float] = [0.0] * self._profile.dimension
        for word in re.findall(r"\w+", text.lower()):
            bucket: int = int(hashlib.sha256(word.encode()).hexdigest(), 16) % len(values)
            values[bucket] += 1.0
        norm: float = math.sqrt(sum(value * value for value in values)) or 1.0
        return Embedding(values=tuple(value / norm for value in values))

    async def embed_documents(self, texts: Sequence[str]) -> list[Embedding]:
        self.calls.append(list(texts))
        for marker, remaining in list(self.failures.items()):
            if remaining > 0 and any(marker in text for text in texts):
                self.failures[marker] = remaining - 1
                raise RuntimeError(f"boom {marker}")
        return [self._vector(text) for text in texts]

    async def embed_query(self, text: str) -> Embedding:
        return self._vector(text)


class FakeChunker(IChunker):
    """One chunk per blank-line separated paragraph."""

    def __init__(self, version: str = "fake-1") -> None:
        self.version: str = version

    @property
    def chunker_version(self) -> str:
        return self.version

    @property
    def extensions(self) -> tuple[str, ...]:
        return (".md",)

    def chunk(self, text: str, path: SourcePath) -> ChunkedDocument:
        parts: list[str] = [part.strip() for part in text.split("\n\n") if part.strip()]
        return ChunkedDocument(
            chunks=tuple(ChunkContent(heading_path=HeadingPath(), text=part) for part in parts),
            warnings=("fake warning",) if "WARN" in text else (),
        )


class FakeSource(IDocumentSource):
    """Files held in a dict; `missing_root` makes the scan fail like a missing folder."""

    def __init__(self, files: dict[str, str] | None = None) -> None:
        self.files: dict[str, str] = files or {}
        self.missing_root: bool = False

    async def scan(
        self, root: str, include: Sequence[str], exclude: Sequence[str]
    ) -> AsyncIterator[SourceFileDTO]:
        if self.missing_root:
            from vectra.exceptions import SourceRootNotFoundError

            raise SourceRootNotFoundError("missing", {"root": root})
        for path, text in sorted(self.files.items()):
            yield SourceFileDTO(
                path=path, content_hash=hashlib.sha256(text.encode()).hexdigest(), size=len(text)
            )

    async def read_text(self, root: str, path: SourcePath) -> str:
        return self.files[path.value]


class FakeRetrievalStore:
    """State shared by every fake repository and unit of work."""

    def __init__(self) -> None:
        self.collections: dict[str, Collection] = {}
        self.documents: dict[tuple[str, str], IndexedDocument] = {}
        self.chunks: dict[tuple[str, str], list[EmbeddedChunk]] = {}
        self.save_failures: dict[str, int] = {}
        self.delete_failures: set[str] = set()
        self.commits: int = 0
        self.hits: list[ChunkHitDTO] = []
        self.last_search: tuple[str, str | None, int] | None = None

    def uow(self) -> FakeUnitOfWork:
        return FakeUnitOfWork(self)

    def manifest(self) -> FakeManifestReadRepository:
        return FakeManifestReadRepository(self)


class _FakeCollectionRepository(ICollectionRepository):
    def __init__(self, store: FakeRetrievalStore) -> None:
        self._store = store

    async def get(self, name: CollectionName) -> Collection | None:
        return self._store.collections.get(name.value)

    async def save(self, collection: Collection) -> None:
        self._store.collections[collection.name.value] = collection

    async def delete(self, name: CollectionName) -> None:
        self._store.collections.pop(name.value, None)
        for key in [key for key in self._store.documents if key[0] == name.value]:
            del self._store.documents[key]
            self._store.chunks.pop(key, None)


class _FakeDocumentRepository(IIndexedDocumentRepository):
    def __init__(self, store: FakeRetrievalStore) -> None:
        self._store = store

    async def get(self, collection: CollectionName, path: SourcePath) -> IndexedDocument | None:
        return self._store.documents.get((collection.value, path.value))

    async def save(self, document: IndexedDocument, chunks: Sequence[EmbeddedChunk]) -> None:
        remaining: int = self._store.save_failures.get(document.path.value, 0)
        if remaining > 0:
            self._store.save_failures[document.path.value] = remaining - 1
            raise RuntimeError("store down")
        key = (document.collection.value, document.path.value)
        self._store.documents[key] = document
        self._store.chunks[key] = list(chunks)

    async def delete(self, collection: CollectionName, path: SourcePath) -> None:
        if path.value in self._store.delete_failures:
            raise RuntimeError("cannot delete")
        self._store.documents.pop((collection.value, path.value), None)
        self._store.chunks.pop((collection.value, path.value), None)


class FakeUnitOfWork(IRetrievalUnitOfWork):
    def __init__(self, store: FakeRetrievalStore) -> None:
        self._store = store
        self._collections = _FakeCollectionRepository(store)
        self._documents = _FakeDocumentRepository(store)

    @property
    def collections(self) -> ICollectionRepository:
        return self._collections

    @property
    def documents(self) -> IIndexedDocumentRepository:
        return self._documents

    async def commit(self) -> None:
        self._store.commits += 1

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class FakeManifestReadRepository(IManifestReadRepository):
    def __init__(self, store: FakeRetrievalStore) -> None:
        self._store = store

    async def stream(self, collection: str) -> AsyncIterator[ManifestEntryDTO]:
        for (name, path), document in sorted(self._store.documents.items()):
            if name == collection:
                yield ManifestEntryDTO(
                    path=path,
                    content_hash=document.content_hash.value,
                    chunker_version=document.chunker_version,
                )


class FakeCollectionReadRepository(ICollectionReadRepository):
    def __init__(self, store: FakeRetrievalStore) -> None:
        self._store = store

    async def list_collections(self) -> list[CollectionStatusDTO]:
        return [self._status(item) for _, item in sorted(self._store.collections.items())]

    async def get_status(self, name: str) -> CollectionStatusDTO | None:
        item: Collection | None = self._store.collections.get(name)
        return self._status(item) if item else None

    def _status(self, item: Collection) -> CollectionStatusDTO:
        keys = [key for key in self._store.documents if key[0] == item.name.value]
        return CollectionStatusDTO(
            name=item.name.value,
            model_id=item.profile.model_id,
            dimension=item.profile.dimension,
            source_root=item.source_root.value,
            created_at=item.created_at,
            document_count=len(keys),
            chunk_count=sum(len(self._store.chunks.get(key, [])) for key in keys),
        )


class FakeChunkSearchReadRepository(IChunkSearchReadRepository):
    def __init__(self, store: FakeRetrievalStore) -> None:
        self._store = store

    async def search(
        self, collection: str, vector: Sequence[float], path_prefix: str | None, limit: int
    ) -> list[ChunkHitDTO]:
        self._store.last_search = (collection, path_prefix, limit)
        return self._store.hits[:limit]


def no_sleep() -> tuple[Callable[[float], Awaitable[None]], list[float]]:
    """A `sleep` replacement recording the requested delays."""
    delays: list[float] = []

    async def sleep(seconds: float) -> None:
        delays.append(seconds)

    return sleep, delays


FIXED_NOW: datetime = datetime(2026, 1, 1, tzinfo=UTC)
