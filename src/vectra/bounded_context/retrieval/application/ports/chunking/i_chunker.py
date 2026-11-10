"""Port to a chunking strategy."""

import abc

from vectra.bounded_context.retrieval.domain.value_objects import ChunkedDocument, SourcePath


class IChunker(abc.ABC):
    """Cuts one kind of document into chunks."""

    @property
    @abc.abstractmethod
    def chunker_version(self) -> str:
        """Changes whenever the cutting rules do, so documents are reindexed."""
        ...

    @property
    @abc.abstractmethod
    def extensions(self) -> tuple[str, ...]:
        """File extensions handled, lowercase with the dot (e.g. `.md`)."""
        ...

    @abc.abstractmethod
    def chunk(self, text: str, path: SourcePath) -> ChunkedDocument:
        """The chunks of `text`, in order."""
        ...
