"""Chooses the chunker for a file."""

from collections.abc import Sequence
from pathlib import PurePosixPath

from vectra.bounded_context.retrieval.application.ports.chunking import IChunker
from vectra.bounded_context.retrieval.domain.value_objects import SourcePath
from vectra.exceptions import ChunkingFailedError


class ChunkerResolver:
    """Maps file extensions to chunkers."""

    def __init__(self, chunkers: Sequence[IChunker]) -> None:
        self._by_extension: dict[str, IChunker] = {
            extension: chunker for chunker in chunkers for extension in chunker.extensions
        }

    def resolve(self, path: SourcePath) -> IChunker:
        """The chunker for `path`'s extension.

        Raises:
            ChunkingFailedError: No chunker handles the extension.
        """
        extension: str = PurePosixPath(path.value).suffix.lower()
        chunker: IChunker | None = self._by_extension.get(extension)
        if chunker is None:
            raise ChunkingFailedError(
                f"No chunker handles {path.value!r}.",
                {"path": path.value, "extension": extension},
                next_steps=[f"Supported extensions: {', '.join(sorted(self._by_extension))}."],
            )
        return chunker
