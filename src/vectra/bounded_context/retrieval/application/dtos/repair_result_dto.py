"""Outcome of rebuilding out-of-sync collections."""

from vectra.utils import FrozenObject

from .sync_result_dto import SyncResultDTO


class SkippedCollectionDTO(FrozenObject):
    """A collection that could not be rebuilt and was left untouched.

    Attributes:
        name: Collection name.
        code: Stable error code.
        message: What went wrong.
    """

    name: str
    code: str
    message: str


class RepairResultDTO(FrozenObject):
    """What a repair did.

    Attributes:
        repaired: Sync results of the rebuilt collections.
        skipped: Collections left untouched, with the reason.
    """

    repaired: tuple[SyncResultDTO, ...]
    skipped: tuple[SkippedCollectionDTO, ...] = ()
