"""Outcome of dropping a collection."""

from vectra.utils import FrozenObject


class DropResultDTO(FrozenObject):
    """A collection was removed.

    Attributes:
        name: Collection name.
        documents: Documents it held.
        chunks: Chunks it held.
    """

    name: str
    documents: int
    chunks: int
