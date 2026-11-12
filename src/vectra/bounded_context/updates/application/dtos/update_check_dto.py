"""Outcome of checking for an update."""

from vectra.utils import FrozenObject


class UpdateCheckDTO(FrozenObject):
    """Installed and latest versions.

    Attributes:
        current: Installed version, as reported by the package.
        latest: Latest release version (`X.Y.Z`), or `None` when none is published.
        update_available: `None` when the installed version is not a release and cannot be compared.
        upgrade_command: Command that installs the latest release, or `None` without one.
    """

    current: str
    latest: str | None
    update_available: bool | None
    upgrade_command: str | None
