"""Bring a collection in line with its source folder."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from functools import partial
from pathlib import PurePosixPath

from vectra.bounded_context.retrieval.application.dtos import (
    FileFailureDTO,
    ManifestEntryDTO,
    SourceFileDTO,
    SyncResultDTO,
)
from vectra.bounded_context.retrieval.application.ports.chunking import IChunker
from vectra.bounded_context.retrieval.application.ports.embedding import IEmbedder
from vectra.bounded_context.retrieval.application.ports.read_repositories import (
    IManifestReadRepository,
)
from vectra.bounded_context.retrieval.application.ports.source import IDocumentSource
from vectra.bounded_context.retrieval.application.ports.uow import IRetrievalUnitOfWork
from vectra.bounded_context.retrieval.application.services import ChunkerResolver
from vectra.bounded_context.retrieval.domain.entities import Collection, IndexedDocument
from vectra.bounded_context.retrieval.domain.policies import (
    StableChunkIdPolicy,
    SyncPlanningPolicy,
)
from vectra.bounded_context.retrieval.domain.value_objects import (
    ChunkedDocument,
    ChunkId,
    CollectionName,
    ContentHash,
    DocumentFingerprint,
    EmbeddedChunk,
    Embedding,
    SourcePath,
    SourceRoot,
    SyncPlan,
)
from vectra.exceptions import AppException, EmbeddingDimensionMismatchError, MassDeleteRefusedError
from vectra.shared_kernel.application.handlers import IHandler
from vectra.utils import FrozenObject

MASS_DELETE_RATIO: float = 0.5
DEFAULT_INCLUDE: tuple[str, ...] = ("**/*.md",)
UNEXPECTED_CODE: str = "RETRIEVAL_000_UNEXPECTED"


class SyncCollectionCommand(FrozenObject):
    """Sync a folder into a collection.

    Attributes:
        collection: Collection name; created on first sync.
        root: Absolute path of the source folder.
        include: Glob patterns to index.
        exclude: Glob patterns to skip.
        dry_run: Plan only; write nothing.
        allow_mass_delete: Permit deleting more than half of the indexed documents.
        rebuild: Drop the collection and recreate it with the current profile and root.
    """

    collection: str
    root: str
    include: tuple[str, ...] = DEFAULT_INCLUDE
    exclude: tuple[str, ...] = ()
    dry_run: bool = False
    allow_mass_delete: bool = False
    rebuild: bool = False


class SyncCollectionHandler(IHandler[SyncCollectionCommand, SyncResultDTO]):
    """Scans, plans and applies changes document by document; one failing file never stops the rest."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], IRetrievalUnitOfWork],
        manifest: IManifestReadRepository,
        source: IDocumentSource,
        resolver: ChunkerResolver,
        embedder: IEmbedder,
        max_retries: int,
        backoff_seconds: float = 0.5,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._uow_factory: Callable[[], IRetrievalUnitOfWork] = uow_factory
        self._manifest: IManifestReadRepository = manifest
        self._source: IDocumentSource = source
        self._resolver: ChunkerResolver = resolver
        self._embedder: IEmbedder = embedder
        self._max_retries: int = max_retries
        self._backoff_seconds: float = backoff_seconds
        self._sleep: Callable[[float], Awaitable[None]] = sleep
        self._clock: Callable[[], datetime] = clock
        self._planning: SyncPlanningPolicy = SyncPlanningPolicy()
        self._chunk_ids: StableChunkIdPolicy = StableChunkIdPolicy()

    async def handle(self, action: SyncCollectionCommand) -> SyncResultDTO:
        """Sync the collection.

        Raises:
            SourceRootInvalidError: The root is missing (nothing is touched).
            SourceRootInvalidError: The collection is bound to another root.
            EmbeddingProfileMismatchError: The configured model differs from the collection's.
            MassDeleteRefusedError: More than half of the indexed documents would be deleted.
        """
        name = CollectionName(value=action.collection)
        root = SourceRoot(value=action.root)
        files: list[SourceFileDTO] = [
            file async for file in self._source.scan(action.root, action.include, action.exclude)
        ]
        collection: Collection | None = await self._existing_collection(name)
        if collection is not None and not action.rebuild:
            collection.assert_same_root(root)
            collection.assert_compatible(self._embedder.profile)

        failures: dict[str, FileFailureDTO] = {}
        scanned: list[DocumentFingerprint] = self._fingerprints(files, failures)
        indexed: list[ManifestEntryDTO] = (
            [] if action.rebuild else [entry async for entry in self._manifest.stream(name.value)]
        )
        plan: SyncPlan = self._planning.plan(
            scanned,
            [
                DocumentFingerprint(
                    path=SourcePath(value=entry.path),
                    content_hash=ContentHash(value=entry.content_hash),
                    chunker_version=entry.chunker_version,
                )
                for entry in indexed
            ],
        )
        self._guard_mass_delete(action, plan, len(indexed))

        created: bool = collection is None or action.rebuild
        if action.dry_run:
            return SyncResultDTO(
                collection=name.value,
                dry_run=True,
                created=created,
                added=_values(plan.add),
                updated=_values(plan.update),
                deleted=_values(plan.delete),
                unchanged=len(plan.unchanged),
                failed=tuple(failures.values()),
            )
        if collection is not None and action.rebuild:
            await self._drop_collection(name)
        if created:
            await self._create_collection(name, root)

        hashes: dict[str, str] = {file.path: file.content_hash for file in files}
        added: list[str] = []
        updated: list[str] = []
        deleted: list[str] = []
        warnings: list[str] = []
        chunks_written: int = 0
        for path in plan.add + plan.update:
            outcome: int | FileFailureDTO = await self._with_retries(
                path, partial(self._index, name, root, path, hashes, warnings)
            )
            if isinstance(outcome, FileFailureDTO):
                failures[path.value] = outcome
            else:
                chunks_written += outcome
                (added if path in plan.add else updated).append(path.value)
        for path in plan.delete:
            result: int | FileFailureDTO = await self._with_retries(
                path, partial(self._remove, name, path)
            )
            if isinstance(result, FileFailureDTO):
                failures[path.value] = result
            else:
                deleted.append(path.value)
        return SyncResultDTO(
            collection=name.value,
            dry_run=False,
            created=created,
            added=tuple(added),
            updated=tuple(updated),
            deleted=tuple(deleted),
            unchanged=len(plan.unchanged),
            failed=tuple(failures.values()),
            warnings=tuple(warnings),
            chunks_written=chunks_written,
        )

    async def _existing_collection(self, name: CollectionName) -> Collection | None:
        async with self._uow_factory() as uow:
            return await uow.collections.get(name)

    async def _drop_collection(self, name: CollectionName) -> None:
        async with self._uow_factory() as uow:
            await uow.collections.delete(name)
            await uow.commit()

    async def _create_collection(self, name: CollectionName, root: SourceRoot) -> None:
        async with self._uow_factory() as uow:
            await uow.collections.save(
                Collection(
                    name=name,
                    profile=self._embedder.profile,
                    source_root=root,
                    created_at=self._clock(),
                )
            )
            await uow.commit()

    def _fingerprints(
        self, files: list[SourceFileDTO], failures: dict[str, FileFailureDTO]
    ) -> list[DocumentFingerprint]:
        """Fingerprints of the files a chunker handles; the others become failures."""
        fingerprints: list[DocumentFingerprint] = []
        for file in files:
            path = SourcePath(value=file.path)
            try:
                chunker: IChunker = self._resolver.resolve(path)
            except AppException as error:
                failures[file.path] = FileFailureDTO(
                    path=file.path, code=error.error_code, message=error.message, attempts=0
                )
                continue
            fingerprints.append(
                DocumentFingerprint(
                    path=path,
                    content_hash=ContentHash(value=file.content_hash),
                    chunker_version=chunker.chunker_version,
                )
            )
        return fingerprints

    def _guard_mass_delete(
        self, action: SyncCollectionCommand, plan: SyncPlan, indexed_count: int
    ) -> None:
        if (
            not action.allow_mass_delete
            and indexed_count > 0
            and len(plan.delete) > indexed_count * MASS_DELETE_RATIO
        ):
            raise MassDeleteRefusedError(
                f"This sync would delete {len(plan.delete)} of {indexed_count} indexed documents.",
                {
                    "collection": action.collection,
                    "to_delete": len(plan.delete),
                    "indexed": indexed_count,
                },
                next_steps=[
                    "Check that the source folder is the right and complete one.",
                    "Repeat with --allow-mass-delete if the deletions are intended.",
                ],
            )

    async def _with_retries(
        self, path: SourcePath, operation: Callable[[], Awaitable[int]]
    ) -> int | FileFailureDTO:
        """Run `operation`, retrying up to `max_retries` times with growing backoff."""
        attempts: int = 0
        while True:
            attempts += 1
            try:
                return await operation()
            except Exception as error:
                if attempts > self._max_retries:
                    code: str = (
                        error.error_code if isinstance(error, AppException) else UNEXPECTED_CODE
                    )
                    message: str = error.message if isinstance(error, AppException) else str(error)
                    return FileFailureDTO(
                        path=path.value, code=code, message=message, attempts=attempts
                    )
                await self._sleep(self._backoff_seconds * attempts)

    async def _index(
        self,
        name: CollectionName,
        root: SourceRoot,
        path: SourcePath,
        hashes: dict[str, str],
        warnings: list[str],
    ) -> int:
        """Chunk, embed and store one document; returns the number of chunks written."""
        chunker: IChunker = self._resolver.resolve(path)
        text: str = await self._source.read_text(root.value, path)
        chunked: ChunkedDocument = chunker.chunk(text, path)
        ids: tuple[ChunkId, ...] = self._chunk_ids.assign(name, path, chunked.chunks)
        embeddings: list[Embedding] = await self._embedder.embed_documents(
            [chunk.text for chunk in chunked.chunks]
        )
        if len(embeddings) != len(chunked.chunks) or any(
            embedding.dimension != self._embedder.profile.dimension for embedding in embeddings
        ):
            raise EmbeddingDimensionMismatchError(
                f"The embedder returned vectors that do not match {self._embedder.profile.fingerprint}.",
                {"path": path.value},
            )
        payload: list[EmbeddedChunk] = [
            EmbeddedChunk(
                chunk_id=chunk_id,
                text=chunk.text,
                heading_path=chunk.heading_path,
                metadata=chunk.metadata,
                embedding=embedding,
            )
            for chunk_id, chunk, embedding in zip(ids, chunked.chunks, embeddings, strict=True)
        ]
        content_hash = ContentHash(value=hashes[path.value])
        async with self._uow_factory() as uow:
            document: IndexedDocument | None = await uow.documents.get(name, path)
            if document is None:
                document = IndexedDocument(
                    collection=name,
                    path=path,
                    content_hash=content_hash,
                    chunker_version=chunker.chunker_version,
                    chunk_ids=ids,
                )
            else:
                document.reindex(content_hash, chunker.chunker_version, ids)
            await uow.documents.save(document, payload)
            await uow.commit()
        warnings.extend(f"{path.value}: {warning}" for warning in chunked.warnings)
        return len(payload)

    async def _remove(self, name: CollectionName, path: SourcePath) -> int:
        async with self._uow_factory() as uow:
            await uow.documents.delete(name, path)
            await uow.commit()
        return 0


def _values(paths: tuple[SourcePath, ...]) -> tuple[str, ...]:
    return tuple(PurePosixPath(path.value).as_posix() for path in paths)
