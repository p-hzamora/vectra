"""Composition root of the CLI: the only place that picks concrete adapters for retrieval."""

from dataclasses import dataclass
from functools import partial
from pathlib import Path

from vectra.bounded_context.configuration.application.handlers.commands import (
    InitEnvFileHandler,
)
from vectra.bounded_context.configuration.infrastructure.outbound.env_file import (
    FilesystemEnvFileWriterAdapter,
)
from vectra.bounded_context.retrieval.application.handlers.commands import (
    DropCollectionHandler,
    RepairCollectionsHandler,
    SyncCollectionHandler,
)
from vectra.bounded_context.retrieval.application.handlers.queries import (
    CheckCollectionProfileHandler,
    ListCollectionsHandler,
    SearchHandler,
)
from vectra.bounded_context.retrieval.application.ports.embedding import IEmbedder
from vectra.bounded_context.retrieval.application.ports.progress import IProgress
from vectra.bounded_context.retrieval.application.services import (
    ChunkerResolver,
    CollectionProvisioner,
    DocumentFingerprinter,
    DocumentIndexer,
    DocumentRemover,
    RetryRunner,
)
from vectra.bounded_context.retrieval.infrastructure.outbound.chunking import (
    MarkdownChunkerAdapter,
    PythonChunkerAdapter,
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
    search: SearchHandler
    drop: DropCollectionHandler
    list_collections: ListCollectionsHandler
    check: CheckCollectionProfileHandler
    repair: RepairCollectionsHandler


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfigurationHandlers:
    """The wired handlers of the configuration context."""

    init: InitEnvFileHandler


def build_configuration() -> ConfigurationHandlers:
    """Wire the configuration handlers over the local filesystem."""
    return ConfigurationHandlers(init=InitEnvFileHandler(writer=FilesystemEnvFileWriterAdapter()))


def build_embedder(environment: Environment) -> IEmbedder:
    """The embedder the settings ask for (the model loads on first use)."""
    return SentenceTransformersEmbedderAdapter(
        environment.retrieval.embedding_model_id, environment.retrieval.embedding_dimension
    )


def build_retrieval(
    environment: Environment,
    *,
    embedder: IEmbedder | None = None,
    backoff_seconds: float = 0.5,
    progress: IProgress | None = None,
) -> RetrievalHandlers:
    """Wire the retrieval handlers over LanceDB under `VECTRA_DATA_DIR`.

    Args:
        environment: Settings of this invocation.
        embedder: Replacement embedder (tests); defaults to `build_embedder`.
        backoff_seconds: Base delay between sync retries.
        progress: Receives progress lines of sync and repair (discarded when `None`).
    """
    store = LanceDbStore(Path(environment.runtime.data_dir) / INDEX_FOLDER)
    chosen: IEmbedder = embedder or build_embedder(environment)
    collections = LanceDbCollectionReadRepositoryAdapter(store)
    uow_factory = partial(LanceDbRetrievalUnitOfWorkAdapter, store)
    source = FilesystemDocumentSourceAdapter()
    profile_check = CheckCollectionProfileHandler(read_repository=collections, embedder=chosen)
    resolver = ChunkerResolver([MarkdownChunkerAdapter(), PythonChunkerAdapter()])
    sync = SyncCollectionHandler(
        manifest=LanceDbManifestReadRepositoryAdapter(store),
        source=source,
        embedder=chosen,
        provisioner=CollectionProvisioner(uow_factory=uow_factory, embedder=chosen),
        fingerprinter=DocumentFingerprinter(resolver),
        indexer=DocumentIndexer(
            uow_factory=uow_factory, source=source, resolver=resolver, embedder=chosen
        ),
        remover=DocumentRemover(uow_factory=uow_factory),
        retry=RetryRunner(
            max_retries=environment.retrieval.sync_max_retries,
            backoff_seconds=backoff_seconds,
        ),
        progress=progress,
    )
    return RetrievalHandlers(
        sync=sync,
        search=SearchHandler(
            profile_check=profile_check,
            chunks=LanceDbChunkSearchReadRepositoryAdapter(store),
            embedder=chosen,
        ),
        drop=DropCollectionHandler(
            uow_factory=uow_factory,
            read_repository=collections,
        ),
        list_collections=ListCollectionsHandler(read_repository=collections),
        check=profile_check,
        repair=RepairCollectionsHandler(check=profile_check, sync=sync, progress=progress),
    )
