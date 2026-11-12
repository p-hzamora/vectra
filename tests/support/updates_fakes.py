"""In-memory stand-ins for the updates ports: nothing here touches the network or an installer."""

from vectra.bounded_context.updates.application.dtos import ReleaseInfoDTO
from vectra.bounded_context.updates.application.ports.installer import (
    IInstallerRunner,
    IInstallMethodDetector,
)
from vectra.bounded_context.updates.application.ports.release_source import IReleaseSource
from vectra.bounded_context.updates.domain.value_objects import InstallMethod, UpgradePlan
from vectra.exceptions import AppException


class FakeReleaseSource(IReleaseSource):
    def __init__(
        self, release: ReleaseInfoDTO | None = None, *, error: AppException | None = None
    ) -> None:
        self.release: ReleaseInfoDTO | None = release
        self.error: AppException | None = error
        self.calls: int = 0

    def latest_release(self) -> ReleaseInfoDTO | None:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.release


class FakeInstallMethodDetector(IInstallMethodDetector):
    def __init__(self, method: InstallMethod | None = None) -> None:
        self.method: InstallMethod | None = method

    def detect(self) -> InstallMethod | None:
        return self.method


class FakeInstallerRunner(IInstallerRunner):
    def __init__(self, *, error: AppException | None = None) -> None:
        self.error: AppException | None = error
        self.plans: list[UpgradePlan] = []

    def run(self, plan: UpgradePlan) -> None:
        self.plans.append(plan)
        if self.error is not None:
            raise self.error
