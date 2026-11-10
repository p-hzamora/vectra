"""Unit of Work of one document (or one collection operation)."""

import abc
from types import TracebackType
from typing import Self

from vectra.bounded_context.retrieval.domain.repositories import (
    ICollectionRepository,
    IIndexedDocumentRepository,
)


class IRetrievalUnitOfWork(abc.ABC):
    """Scope of one write. The store has no cross-table transaction: `commit` marks the scope
    as finished, and the repositories order their writes (manifest last) so a crash is
    repaired by the next sync."""

    @property
    @abc.abstractmethod
    def collections(self) -> ICollectionRepository:
        """The collection repository of this unit of work."""
        ...

    @property
    @abc.abstractmethod
    def documents(self) -> IIndexedDocumentRepository:
        """The indexed-document repository of this unit of work."""
        ...

    @abc.abstractmethod
    async def commit(self) -> None:
        """Finish the scope successfully."""
        ...

    @abc.abstractmethod
    async def __aenter__(self) -> Self: ...

    @abc.abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
