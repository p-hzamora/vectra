"""Port to where documents live."""

import abc
from collections.abc import AsyncIterator, Sequence

from vectra.bounded_context.retrieval.application.dtos import SourceFileDTO
from vectra.bounded_context.retrieval.domain.value_objects import SourcePath


class IDocumentSource(abc.ABC):
    """Lists and reads documents under a root."""

    @abc.abstractmethod
    def scan(
        self, root: str, include: Sequence[str], exclude: Sequence[str]
    ) -> AsyncIterator[SourceFileDTO]:
        """Files under `root` matching `include` and not `exclude` (glob patterns).

        Raises:
            SourceRootNotFoundError: `root` is missing or not a folder.
        """
        ...

    @abc.abstractmethod
    async def read_text(self, root: str, path: SourcePath) -> str:
        """The file's text.

        Raises:
            DocumentReadError: The file cannot be read or decoded.
        """
        ...
