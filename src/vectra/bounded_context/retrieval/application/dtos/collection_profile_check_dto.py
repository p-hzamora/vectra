"""Whether a collection's embeddings match the configured model."""

from vectra.utils import FrozenObject


class CollectionProfileCheckDTO(FrozenObject):
    """One collection compared with the configured embedding profile.

    Attributes:
        name: Collection name.
        model_id: Model the collection was built with.
        dimension: Vector length the collection was built with.
        configured_model_id: Model the settings ask for.
        configured_dimension: Vector length the settings ask for.
        in_sync: Whether both profiles are equal.
    """

    name: str
    model_id: str
    dimension: int
    configured_model_id: str
    configured_dimension: int
    in_sync: bool


class CollectionProfileCheckListDTO(FrozenObject):
    """Result of checking collections.

    Attributes:
        collections: Checked collections sorted by name.
    """

    collections: tuple[CollectionProfileCheckDTO, ...]

    @property
    def in_sync(self) -> bool:
        """Whether every collection matches the configured profile."""
        return all(item.in_sync for item in self.collections)
