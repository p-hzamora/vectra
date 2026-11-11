"""Outcome of indexing one document."""

from vectra.utils import FrozenObject


class DocumentIndexResultDTO(FrozenObject):
    """What indexing one document produced.

    Attributes:
        chunks_written: Chunks stored for the document.
        warnings: Chunker warnings, already prefixed with the document path.
    """

    chunks_written: int
    warnings: tuple[str, ...] = ()
