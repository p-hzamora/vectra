"""One search result: the best chunk of a document."""

from vectra.utils import FrozenObject


class DocumentHitDTO(FrozenObject):
    """A matching document.

    Attributes:
        rank: Position in the result list, 1 for the best document.
        path: Document path.
        score: Best chunk score, 0..1 higher is better.
        heading_path: Headings above the best chunk.
        snippet: Start of the best chunk's text.
        chunk_id: Id of the best chunk.
    """

    rank: int
    path: str
    score: float
    heading_path: tuple[str, ...]
    snippet: str
    chunk_id: str
