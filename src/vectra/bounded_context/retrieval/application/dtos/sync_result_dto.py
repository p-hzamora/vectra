"""Outcome of a sync."""

from vectra.utils import FrozenObject

from .file_failure_dto import FileFailureDTO


class SyncResultDTO(FrozenObject):
    """What a sync did (or, with `dry_run`, would do).

    Attributes:
        collection: Collection name.
        dry_run: Nothing was written.
        created: The collection was (or would be) created by this sync.
        added: Documents added.
        updated: Documents reindexed.
        deleted: Documents removed.
        unchanged: Documents already current.
        failed: Files that could not be processed, after retries.
        warnings: Non-fatal problems worth a look.
        chunks_written: Chunks written (0 in a dry run).
    """

    collection: str
    dry_run: bool
    created: bool
    added: tuple[str, ...]
    updated: tuple[str, ...]
    deleted: tuple[str, ...]
    unchanged: int
    failed: tuple[FileFailureDTO, ...] = ()
    warnings: tuple[str, ...] = ()
    chunks_written: int = 0
