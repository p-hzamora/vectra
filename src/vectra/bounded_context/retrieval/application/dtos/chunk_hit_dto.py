"""One chunk returned by the vector store."""

from vectra.utils import FrozenObject


class ChunkHitDTO(FrozenObject):
    """A matching chunk.

    Attributes:
        chunk_id: Stable chunk id.
        path: Document path.
        heading_path: Headings above the chunk.
        text: Chunk text.
        score: Similarity normalized to 0..1, higher is better.
    """

    chunk_id: str
    path: str
    heading_path: tuple[str, ...]
    text: str
    score: float
