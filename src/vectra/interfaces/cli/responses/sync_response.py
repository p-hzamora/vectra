"""`vectra sync` output."""

from vectra.utils import FrozenObject

from .i_renderable_response import IRenderableResponse


class FileFailureResponse(FrozenObject):
    """A file that could not be indexed.

    Attributes:
        path: Document path.
        code: Stable error code of the last failure.
        message: What went wrong.
        attempts: Times the file was tried.
    """

    path: str
    code: str
    message: str
    attempts: int


class SyncResponse(IRenderableResponse):
    """What a sync did (or would do with `dry_run`).

    Attributes:
        collection: Collection name.
        dry_run: Nothing was written.
        created: The collection was (or would be) created.
        added: Documents added.
        updated: Documents reindexed.
        deleted: Documents removed.
        unchanged: Documents already current.
        failed: Files that could not be processed.
        warnings: Non-fatal problems.
        chunks_written: Chunks written.
    """

    collection: str
    dry_run: bool
    created: bool
    added: tuple[str, ...]
    updated: tuple[str, ...]
    deleted: tuple[str, ...]
    unchanged: int
    failed: tuple[FileFailureResponse, ...]
    warnings: tuple[str, ...]
    chunks_written: int

    def render(self) -> str:
        verb: str = "would " if self.dry_run else ""
        lines: list[str] = [
            f"collection {self.collection}{' (new)' if self.created else ''}"
            f"{' [dry run]' if self.dry_run else ''}",
            f"  {verb}add {len(self.added)}, {verb}update {len(self.updated)}, "
            f"{verb}delete {len(self.deleted)}, unchanged {self.unchanged}",
        ]
        if not self.dry_run:
            lines.append(f"  chunks written: {self.chunks_written}")
        lines += [f"  warning: {warning}" for warning in self.warnings]
        lines += [
            f"  failed {item.path} [{item.code}] after {item.attempts} attempt(s): {item.message}"
            for item in self.failed
        ]
        return "\n".join(lines)


class SkippedCollectionResponse(FrozenObject):
    """A collection left untouched by a repair.

    Attributes:
        name: Collection name.
        code: Stable error code.
        message: What went wrong.
    """

    name: str
    code: str
    message: str


class RepairResponse(IRenderableResponse):
    """`vectra collections check --fix`.

    Attributes:
        repaired: Rebuilt collections.
        skipped: Collections left untouched, with the reason.
    """

    repaired: tuple[SyncResponse, ...]
    skipped: tuple[SkippedCollectionResponse, ...]

    def render(self) -> str:
        if not self.repaired and not self.skipped:
            return "nothing to repair"
        lines: list[str] = [item.render() for item in self.repaired]
        lines += [f"skipped {item.name} [{item.code}]: {item.message}" for item in self.skipped]
        return "\n".join(lines)
