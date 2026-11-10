"""Port to an embedding model."""

import abc
from collections.abc import Sequence

from vectra.bounded_context.retrieval.domain.value_objects import Embedding, EmbeddingProfile


class IEmbedder(abc.ABC):
    """Turns text into vectors. Queries and documents may be prepared differently."""

    @property
    @abc.abstractmethod
    def profile(self) -> EmbeddingProfile:
        """Model id and dimension this embedder produces."""
        ...

    @abc.abstractmethod
    async def embed_documents(self, texts: Sequence[str]) -> list[Embedding]:
        """One embedding per text, in order."""
        ...

    @abc.abstractmethod
    async def embed_query(self, text: str) -> Embedding:
        """The embedding of a search query."""
        ...
