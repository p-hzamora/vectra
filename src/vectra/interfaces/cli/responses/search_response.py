"""`vectra search` output."""

from vectra.utils import FrozenObject

from .i_renderable_response import IRenderableResponse


class SearchHitResponse(FrozenObject):
    """The best chunk of one document.

    Attributes:
        path: Document path.
        score: 0..1, higher is better.
        heading_path: Headings above the chunk.
        snippet: Start of the chunk text.
        chunk_id: Chunk id.
    """

    path: str
    score: float
    heading_path: tuple[str, ...]
    snippet: str
    chunk_id: str


class SearchResponse(IRenderableResponse):
    """Documents matching a query, best first.

    Attributes:
        collection: Collection searched.
        query: The query text.
        hits: One entry per document.
    """

    collection: str
    query: str
    hits: tuple[SearchHitResponse, ...]

    def render(self) -> str:
        if not self.hits:
            return "no results"
        blocks: list[str] = []
        for hit in self.hits:
            heading: str = " > ".join(hit.heading_path)
            title: str = f"{hit.path}  {hit.score:.3f}" + (f"  [{heading}]" if heading else "")
            blocks.append(f"{title}\n  {hit.snippet}")
        return "\n".join(blocks)
