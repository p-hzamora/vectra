"""Compare the installed version with the latest release."""

from vectra.bounded_context.updates.application.dtos import UpdateCheckDTO
from vectra.bounded_context.updates.application.ports.installer import IInstallMethodDetector
from vectra.bounded_context.updates.application.ports.release_source import IReleaseSource
from vectra.bounded_context.updates.domain.policies import (
    UpdateAvailabilityPolicy,
    UpgradePlanPolicy,
)
from vectra.bounded_context.updates.domain.value_objects import InstallMethod, ReleaseTag
from vectra.shared_kernel.application.handlers import IHandler
from vectra.utils import FrozenObject


class CheckForUpdateQuery(FrozenObject):
    """Ask whether a newer release exists.

    Attributes:
        current: Installed version string.
    """

    current: str


class CheckForUpdateHandler(IHandler[CheckForUpdateQuery, UpdateCheckDTO]):
    """Reads the latest release and reports the command that would install it."""

    def __init__(self, *, release_source: IReleaseSource, detector: IInstallMethodDetector) -> None:
        self._release_source: IReleaseSource = release_source
        self._detector: IInstallMethodDetector = detector
        self._availability = UpdateAvailabilityPolicy()
        self._plans = UpgradePlanPolicy()

    async def handle(self, action: CheckForUpdateQuery) -> UpdateCheckDTO:
        """Check for an update.

        Raises:
            ReleaseSourceUnavailableError: The release source could not be read.
        """
        release = self._release_source.latest_release()
        latest: ReleaseTag | None = (
            self._availability.accepted_tag(
                tag_name=release.tag_name, prerelease=release.prerelease, draft=release.draft
            )
            if release
            else None
        )
        available: bool | None = self._availability.availability(
            current=self._availability.current(action.current), latest=latest
        )
        command: str | None = None
        if latest is not None:
            method: InstallMethod | None = self._detector.detect()
            command = (
                self._plans.plan(method, latest).command
                if method
                else self._plans.manual_command(latest)
            )
        return UpdateCheckDTO(
            current=action.current,
            latest=str(latest.version) if latest else None,
            update_available=available,
            upgrade_command=command,
        )
