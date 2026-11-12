"""Reinstall vectra at the latest release."""

from vectra.bounded_context.updates.application.dtos import UpdateAppliedDTO
from vectra.bounded_context.updates.application.ports.installer import (
    IInstallerRunner,
    IInstallMethodDetector,
)
from vectra.bounded_context.updates.application.ports.release_source import IReleaseSource
from vectra.bounded_context.updates.domain.policies import (
    UpdateAvailabilityPolicy,
    UpgradePlanPolicy,
)
from vectra.bounded_context.updates.domain.value_objects import (
    InstallMethod,
    ReleaseTag,
    UpgradePlan,
    Version,
)
from vectra.exceptions import (
    InstallerNotDetectedError,
    InvalidVersionError,
    NoReleasePublishedError,
)
from vectra.shared_kernel.application.handlers import IHandler
from vectra.utils import FrozenObject


class ApplyUpdateCommand(FrozenObject):
    """Upgrade to the latest release.

    Attributes:
        current: Installed version string.
    """

    current: str


class ApplyUpdateHandler(IHandler[ApplyUpdateCommand, UpdateAppliedDTO]):
    """Runs the upgrade plan of the detected installer; never runs `install.sh`."""

    def __init__(
        self,
        *,
        release_source: IReleaseSource,
        detector: IInstallMethodDetector,
        runner: IInstallerRunner,
    ) -> None:
        self._release_source: IReleaseSource = release_source
        self._detector: IInstallMethodDetector = detector
        self._runner: IInstallerRunner = runner
        self._availability = UpdateAvailabilityPolicy()
        self._plans = UpgradePlanPolicy()

    async def handle(self, action: ApplyUpdateCommand) -> UpdateAppliedDTO:
        """Upgrade when a newer release exists.

        Raises:
            ReleaseSourceUnavailableError: The release source could not be read.
            NoReleasePublishedError: There is no usable release.
            InvalidVersionError: The installed version is not a release version.
            InstallerNotDetectedError: The install cannot be upgraded by vectra.
            UpgradeFailedError: The installer failed.
        """
        release = self._release_source.latest_release()
        latest: ReleaseTag | None = (
            self._availability.accepted_tag(
                tag_name=release.tag_name, prerelease=release.prerelease, draft=release.draft
            )
            if release
            else None
        )
        if latest is None:
            raise NoReleasePublishedError(
                "No release of vectra has been published.",
                next_steps=[
                    "Run `vectra update --check` later, or reinstall from `main` with install.sh."
                ],
            )
        manual: str = self._plans.manual_command(latest)
        try:
            current: Version = Version.parse(action.current)
        except InvalidVersionError as error:
            raise InvalidVersionError(
                f"The installed version {action.current!r} is not a release version.",
                {"version": action.current},
                next_steps=[f"Reinstall a release by hand: {manual}"],
            ) from error
        if not latest.version.is_newer_than(current):
            return UpdateAppliedDTO(
                current=action.current,
                latest=str(latest.version),
                applied=False,
                upgrade_command=None,
            )
        method: InstallMethod | None = self._detector.detect()
        if method is None:
            raise InstallerNotDetectedError(
                "Cannot tell how vectra was installed, so it will not upgrade itself.",
                {"latest": str(latest)},
                next_steps=[
                    f"Upgrade by hand: {manual}",
                    "Editable installs, Windows and ambiguous installs are not upgraded by vectra.",
                ],
            )
        plan: UpgradePlan = self._plans.plan(method, latest)
        self._runner.run(plan)
        return UpdateAppliedDTO(
            current=action.current,
            latest=str(latest.version),
            applied=True,
            upgrade_command=plan.command,
        )
