"""Check collections against the configured embedding model."""

from vectra.bounded_context.retrieval.application.dtos import (
    CollectionProfileCheckDTO,
    CollectionProfileCheckListDTO,
    CollectionStatusDTO,
)
from vectra.bounded_context.retrieval.application.ports.embedding import IEmbedder
from vectra.bounded_context.retrieval.application.ports.read_repositories import (
    ICollectionReadRepository,
)
from vectra.bounded_context.retrieval.domain.value_objects import EmbeddingProfile
from vectra.exceptions import CollectionNotFoundError
from vectra.shared_kernel.application.handlers import IHandler
from vectra.utils import FrozenObject


class CheckCollectionProfileQuery(FrozenObject):
    """Check one collection, or every collection.

    Attributes:
        collection: Collection name; `None` checks all of them.
    """

    collection: str | None = None


class CheckCollectionProfileHandler(
    IHandler[CheckCollectionProfileQuery, CollectionProfileCheckListDTO]
):
    """Compares each collection's stored profile with the embedder's, without loading the model."""

    def __init__(self, *, read_repository: ICollectionReadRepository, embedder: IEmbedder) -> None:
        self._read_repository: ICollectionReadRepository = read_repository
        self._embedder: IEmbedder = embedder

    async def handle(self, action: CheckCollectionProfileQuery) -> CollectionProfileCheckListDTO:
        """The comparison per collection.

        Raises:
            CollectionNotFoundError: A name was given and there is no such collection.
        """
        statuses: list[CollectionStatusDTO]
        if action.collection is None:
            statuses = await self._read_repository.list_collections()
        else:
            status = await self._read_repository.get_status(action.collection)
            if status is None:
                raise CollectionNotFoundError(
                    f"No collection named {action.collection!r}.",
                    {"collection": action.collection},
                    next_steps=["Run `vectra collections list`, or `vectra sync` to create it."],
                )
            statuses = [status]
        configured: EmbeddingProfile = self._embedder.profile
        return CollectionProfileCheckListDTO(
            collections=tuple(
                CollectionProfileCheckDTO(
                    name=status.name,
                    model_id=status.model_id,
                    dimension=status.dimension,
                    configured_model_id=configured.model_id,
                    configured_dimension=configured.dimension,
                    in_sync=configured
                    == EmbeddingProfile(model_id=status.model_id, dimension=status.dimension),
                )
                for status in statuses
            )
        )
