"""Read model of what is indexed."""

import abc
from collections.abc import AsyncIterator

from vectra.bounded_context.retrieval.application.dtos import ManifestEntryDTO


class IManifestReadRepository(abc.ABC):
    """Streams the manifest of a collection."""

    @abc.abstractmethod
    def stream(self, collection: str) -> AsyncIterator[ManifestEntryDTO]:
        """Every indexed document of `collection` (nothing for an unknown collection)."""
        ...
