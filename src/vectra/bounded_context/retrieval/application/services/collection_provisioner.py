"""Creates, loads and drops collections."""

from collections.abc import Callable
from datetime import UTC, datetime

from vectra.bounded_context.retrieval.application.ports.embedding import IEmbedder
from vectra.bounded_context.retrieval.application.ports.uow import IRetrievalUnitOfWork
from vectra.bounded_context.retrieval.domain.entities import Collection
from vectra.bounded_context.retrieval.domain.value_objects import CollectionName, SourceRoot


class CollectionProvisioner:
    """Each operation is its own unit of work."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], IRetrievalUnitOfWork],
        embedder: IEmbedder,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._uow_factory: Callable[[], IRetrievalUnitOfWork] = uow_factory
        self._embedder: IEmbedder = embedder
        self._clock: Callable[[], datetime] = clock

    async def get(self, name: CollectionName) -> Collection | None:
        """The collection, or `None` when it does not exist."""
        async with self._uow_factory() as uow:
            return await uow.collections.get(name)

    async def drop(self, name: CollectionName) -> None:
        """Remove the collection with everything indexed in it."""
        async with self._uow_factory() as uow:
            await uow.collections.delete(name)
            await uow.commit()

    async def create(self, name: CollectionName, root: SourceRoot) -> None:
        """Create the collection with the embedder's current profile, bound to `root`."""
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
