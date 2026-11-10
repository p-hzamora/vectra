"""A file found by a document source."""

from vectra.utils import FrozenObject


class SourceFileDTO(FrozenObject):
    """One scanned file.

    Attributes:
        path: Path relative to the root, POSIX style.
        content_hash: SHA-256 of its bytes.
        size: Size in bytes.
    """

    path: str
    content_hash: str
    size: int
