"""Composition root of the CLI: the only place that picks concrete adapters for retrieval."""

from dataclasses import dataclass
from functools import partial
from pathlib import Path

from vectra.bounded_context.retrieval.application.handlers.commands import (
    DropCollectionHandler,
    SyncCollectionHandler,
)
from vectra.bounded_context.retrieval.application.handlers.queries import (
    ListCollectionsHandler,
    SearchCollectionHandler,
)
from vectra.bounded_context.retrieval.application.ports.embedding import IEmbedder
from vectra.bounded_context.retrieval.application.services import ChunkerResolver
from vectra.bounded_context.retrieval.infrastructure.outbound.chunking import (
    MarkdownChunkerAdapter,
)
from vectra.bounded_context.retrieval.infrastructure.outbound.embedding import (
    SentenceTransformersEmbedderAdapter,
)
from vectra.bounded_context.retrieval.infrastructure.outbound.source import (
    FilesystemDocumentSourceAdapter,
)
from vectra.bounded_context.retrieval.infrastructure.outbound.vector_store import (
    LanceDbChunkSearchReadRepositoryAdapter,
    LanceDbCollectionReadRepositoryAdapter,
    LanceDbManifestReadRepositoryAdapter,
    LanceDbRetrievalUnitOfWorkAdapter,
    LanceDbStore,
)
from vectra.core import Environment

INDEX_FOLDER: str = "index"


@dataclass(frozen=True, slots=True, kw_only=True)
class RetrievalHandlers:
    """The wired handlers of the retrieval context."""

    sync: SyncCollectionHandler
    search: SearchCollectionHandler
    drop: DropCollectionHandler
    list_collections: ListCollectionsHandler


def build_embedder(environment: Environment) -> IEmbedder:
    """The embedder the settings ask for (the model loads on first use)."""
    return SentenceTransformersEmbedderAdapter(
        environment.retrieval.embedding_model_id, environment.retrieval.embedding_dimension
    )


def build_retrieval(
    environment: Environment, *, embedder: IEmbedder | None = None, backoff_seconds: float = 0.5
) -> RetrievalHandlers:
    """Wire the retrieval handlers over LanceDB under `VECTRA_DATA_DIR`.

    Args:
        environment: Settings of this invocation.
        embedder: Replacement embedder (tests); defaults to `build_embedder`.
        backoff_seconds: Base delay between sync retries.
    """
    store = LanceDbStore(Path(environment.runtime.data_dir) / INDEX_FOLDER)
    chosen: IEmbedder = embedder or build_embedder(environment)
    collections = LanceDbCollectionReadRepositoryAdapter(store)
    return RetrievalHandlers(
        sync=SyncCollectionHandler(
            uow_factory=partial(LanceDbRetrievalUnitOfWorkAdapter, store),
            manifest=LanceDbManifestReadRepositoryAdapter(store),
            source=FilesystemDocumentSourceAdapter(),
            resolver=ChunkerResolver([MarkdownChunkerAdapter()]),
            embedder=chosen,
            max_retries=environment.retrieval.sync_max_retries,
            backoff_seconds=backoff_seconds,
        ),
        search=SearchCollectionHandler(
            collections=collections,
            chunks=LanceDbChunkSearchReadRepositoryAdapter(store),
            embedder=chosen,
        ),
        drop=DropCollectionHandler(
            uow_factory=partial(LanceDbRetrievalUnitOfWorkAdapter, store),
            read_repository=collections,
        ),
        list_collections=ListCollectionsHandler(read_repository=collections),
    )
