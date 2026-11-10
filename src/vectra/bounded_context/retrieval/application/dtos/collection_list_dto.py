"""Every collection."""

from vectra.utils import FrozenObject

from .collection_status_dto import CollectionStatusDTO


class CollectionListDTO(FrozenObject):
    """Result of listing collections.

    Attributes:
        collections: Collections sorted by name.
    """

    collections: tuple[CollectionStatusDTO, ...]
