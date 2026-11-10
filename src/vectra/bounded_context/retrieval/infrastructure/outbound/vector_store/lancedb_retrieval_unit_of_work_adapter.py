"""Unit of Work over the LanceDB repositories."""

from types import TracebackType
from typing import Self

from vectra.bounded_context.retrieval.application.ports.uow import IRetrievalUnitOfWork
from vectra.bounded_context.retrieval.domain.repositories import (
    ICollectionRepository,
    IIndexedDocumentRepository,
)

from .lancedb_collection_repository_adapter import LanceDbCollectionRepositoryAdapter
from .lancedb_indexed_document_repository_adapter import (
    LanceDbIndexedDocumentRepositoryAdapter,
)
from .lancedb_store import LanceDbStore


class LanceDbRetrievalUnitOfWorkAdapter(IRetrievalUnitOfWork):
    """Hands out the repositories. LanceDB has no multi-table transaction, so repositories write
    immediately in a crash-safe order and `commit` is a marker that the scope finished."""

    def __init__(self, store: LanceDbStore) -> None:
        self._collections: ICollectionRepository = LanceDbCollectionRepositoryAdapter(store)
        self._documents: IIndexedDocumentRepository = LanceDbIndexedDocumentRepositoryAdapter(store)
        self.committed: bool = False

    @property
    def collections(self) -> ICollectionRepository:
        return self._collections

    @property
    def documents(self) -> IIndexedDocumentRepository:
        return self._documents

    async def commit(self) -> None:
        self.committed = True

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None
