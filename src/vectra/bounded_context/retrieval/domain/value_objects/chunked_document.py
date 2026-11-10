"""Result of chunking one document."""

from vectra.utils import FrozenObject

from .chunk_content import ChunkContent


class ChunkedDocument(FrozenObject):
    """Chunks plus anything worth telling the user.

    Attributes:
        chunks: Chunks in document order.
        warnings: Non-fatal problems, e.g. malformed frontmatter ignored.
    """

    chunks: tuple[ChunkContent, ...]
    warnings: tuple[str, ...] = ()
