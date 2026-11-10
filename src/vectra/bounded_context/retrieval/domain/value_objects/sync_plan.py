"""What a sync will do, computed before touching the store."""

from vectra.utils import FrozenObject

from .source_path import SourcePath


class SyncPlan(FrozenObject):
    """Document paths grouped by action, each sorted.

    Attributes:
        add: On disk, not indexed.
        update: Indexed, but hash or chunker version differs.
        delete: Indexed, no longer on disk.
        unchanged: Indexed and current.
    """

    add: tuple[SourcePath, ...] = ()
    update: tuple[SourcePath, ...] = ()
    delete: tuple[SourcePath, ...] = ()
    unchanged: tuple[SourcePath, ...] = ()
