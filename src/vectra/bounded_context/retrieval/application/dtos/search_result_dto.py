"""Outcome of a search."""

from vectra.utils import FrozenObject

from .document_hit_dto import DocumentHitDTO


class SearchResultDTO(FrozenObject):
    """Documents matching a query, best first.

    Attributes:
        collection: Collection searched.
        query: The query text.
        hits: One entry per document.
    """

    collection: str
    query: str
    hits: tuple[DocumentHitDTO, ...]
