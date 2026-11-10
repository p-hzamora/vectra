"""Decides which documents to add, update, delete or leave alone."""

from collections.abc import Sequence

from vectra.bounded_context.retrieval.domain.value_objects import (
    DocumentFingerprint,
    SourcePath,
    SyncPlan,
)


class SyncPlanningPolicy:
    """Compares what is on disk with what is indexed. A document is stale when its content
    hash or its chunker version differs."""

    def plan(
        self, scanned: Sequence[DocumentFingerprint], indexed: Sequence[DocumentFingerprint]
    ) -> SyncPlan:
        """The plan; every group is sorted by path."""
        on_disk: dict[SourcePath, DocumentFingerprint] = {item.path: item for item in scanned}
        known: dict[SourcePath, DocumentFingerprint] = {item.path: item for item in indexed}
        add: list[SourcePath] = []
        update: list[SourcePath] = []
        unchanged: list[SourcePath] = []
        for path, fingerprint in on_disk.items():
            current: DocumentFingerprint | None = known.get(path)
            if current is None:
                add.append(path)
            elif current != fingerprint:
                update.append(path)
            else:
                unchanged.append(path)
        delete: list[SourcePath] = [path for path in known if path not in on_disk]
        return SyncPlan(
            add=_ordered(add),
            update=_ordered(update),
            delete=_ordered(delete),
            unchanged=_ordered(unchanged),
        )


def _ordered(paths: list[SourcePath]) -> tuple[SourcePath, ...]:
    return tuple(sorted(paths, key=lambda path: path.value))
