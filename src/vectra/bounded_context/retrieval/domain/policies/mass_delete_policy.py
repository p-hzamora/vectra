"""Guards against a sync that would wipe most of a collection."""

from vectra.exceptions import MassDeleteRefusedError

MASS_DELETE_RATIO: float = 0.5


class MassDeletePolicy:
    """A sync deleting more than `MASS_DELETE_RATIO` of the indexed documents is suspect
    (wrong or incomplete source folder) and needs an explicit opt-in."""

    def refusal(
        self, *, collection: str, to_delete: int, indexed: int, allowed: bool
    ) -> MassDeleteRefusedError | None:
        """The error a real sync would raise, or `None` when the deletion is acceptable.

        Args:
            collection: Collection name, for the message.
            to_delete: Documents the plan deletes.
            indexed: Documents currently indexed.
            allowed: The caller opted in to mass deletion.
        """
        if allowed or indexed == 0 or to_delete <= indexed * MASS_DELETE_RATIO:
            return None
        return MassDeleteRefusedError(
            f"This sync would delete {to_delete} of {indexed} indexed documents.",
            {"collection": collection, "to_delete": to_delete, "indexed": indexed},
            next_steps=[
                "Check that the source folder is the right and complete one.",
                "Repeat with --allow-mass-delete if the deletions are intended.",
            ],
        )
