"""Chunks, embeds and stores one document."""

from collections.abc import Callable

from vectra.bounded_context.retrieval.application.dtos import DocumentIndexResultDTO
from vectra.bounded_context.retrieval.application.ports.chunking import IChunker
from vectra.bounded_context.retrieval.application.ports.embedding import IEmbedder
from vectra.bounded_context.retrieval.application.ports.source import IDocumentSource
from vectra.bounded_context.retrieval.application.ports.uow import IRetrievalUnitOfWork
from vectra.bounded_context.retrieval.application.services.chunker_resolver import (
    ChunkerResolver,
)
from vectra.bounded_context.retrieval.domain.entities import IndexedDocument
from vectra.bounded_context.retrieval.domain.policies import StableChunkIdPolicy
from vectra.bounded_context.retrieval.domain.value_objects import (
    ChunkedDocument,
    ChunkId,
    CollectionName,
    ContentHash,
    EmbeddedChunk,
    Embedding,
    SourcePath,
    SourceRoot,
)


class DocumentIndexer:
    """Reads a document, cuts and embeds it, and replaces what the collection holds for it."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], IRetrievalUnitOfWork],
        source: IDocumentSource,
        resolver: ChunkerResolver,
        embedder: IEmbedder,
    ) -> None:
        self._uow_factory: Callable[[], IRetrievalUnitOfWork] = uow_factory
        self._source: IDocumentSource = source
        self._resolver: ChunkerResolver = resolver
        self._embedder: IEmbedder = embedder
        self._chunk_ids: StableChunkIdPolicy = StableChunkIdPolicy()

    async def index(
        self, name: CollectionName, root: SourceRoot, path: SourcePath, content_hash: str
    ) -> DocumentIndexResultDTO:
        """Index one document.

        Args:
            name: Target collection.
            root: Source root the document is read from.
            path: Document path under `root`.
            content_hash: Hash of the bytes the scan saw.

        Raises:
            ChunkingFailedError: No chunker handles the document.
            EmbeddingDimensionMismatchError: The embedder returned unusable vectors.
        """
        chunker: IChunker = self._resolver.resolve(path)
        text: str = await self._source.read_text(root.value, path)
        chunked: ChunkedDocument = chunker.chunk(text, path)
        ids: tuple[ChunkId, ...] = self._chunk_ids.assign(name, path, chunked.chunks)
        embeddings: list[Embedding] = await self._embedder.embed_documents(
            [chunk.text for chunk in chunked.chunks]
        )
        self._embedder.profile.assert_embeddings(embeddings, len(chunked.chunks), path.value)
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
        hashed = ContentHash(value=content_hash)
        async with self._uow_factory() as uow:
            document: IndexedDocument | None = await uow.documents.get(name, path)
            if document is None:
                document = IndexedDocument(
                    collection=name,
                    path=path,
                    content_hash=hashed,
                    chunker_version=chunker.chunker_version,
                    chunk_ids=ids,
                )
            else:
                document.reindex(hashed, chunker.chunker_version, ids)
            await uow.documents.save(document, payload)
            await uow.commit()
        return DocumentIndexResultDTO(
            chunks_written=len(payload),
            warnings=tuple(f"{path.value}: {warning}" for warning in chunked.warnings),
        )
