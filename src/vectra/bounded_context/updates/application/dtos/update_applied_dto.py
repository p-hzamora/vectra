"""Outcome of applying an update."""

from vectra.utils import FrozenObject


class UpdateAppliedDTO(FrozenObject):
    """What `--apply` did.

    Attributes:
        current: Version installed before.
        latest: Latest release version (`X.Y.Z`).
        applied: Whether an installer ran (`False` when already up to date).
        upgrade_command: The command that ran, or `None` when nothing ran.
    """

    current: str
    latest: str
    applied: bool
    upgrade_command: str | None
