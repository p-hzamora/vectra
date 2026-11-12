"""`vectra update` use cases against fakes."""

import pytest

from tests.support.updates_fakes import (
    FakeInstallerRunner,
    FakeInstallMethodDetector,
    FakeReleaseSource,
)
from vectra.bounded_context.updates.application.dtos import ReleaseInfoDTO
from vectra.bounded_context.updates.application.handlers.commands import (
    ApplyUpdateCommand,
    ApplyUpdateHandler,
)
from vectra.bounded_context.updates.application.handlers.queries import (
    CheckForUpdateHandler,
    CheckForUpdateQuery,
)
from vectra.bounded_context.updates.domain.value_objects import InstallerKind, InstallMethod
from vectra.exceptions import (
    InstallerNotDetectedError,
    InvalidVersionError,
    NoReleasePublishedError,
    ReleaseSourceUnavailableError,
    UpgradeFailedError,
)

pytestmark = pytest.mark.unit

UV = InstallMethod(kind=InstallerKind.UV)
UV_COMMAND = (
    "uv tool install --force --python '>=3.14' git+https://github.com/p-hzamora/vectra@v0.4.0"
)
MANUAL = "curl -LsSf https://raw.githubusercontent.com/p-hzamora/vectra/main/install.sh | VECTRA_REF=v0.4.0 sh"


def release(
    tag: str = "v0.4.0", *, prerelease: bool = False, draft: bool = False
) -> ReleaseInfoDTO:
    return ReleaseInfoDTO(tag_name=tag, prerelease=prerelease, draft=draft)


def checker(source: FakeReleaseSource, method: InstallMethod | None = UV) -> CheckForUpdateHandler:
    return CheckForUpdateHandler(release_source=source, detector=FakeInstallMethodDetector(method))


def applier(
    source: FakeReleaseSource,
    runner: FakeInstallerRunner,
    method: InstallMethod | None = UV,
) -> ApplyUpdateHandler:
    return ApplyUpdateHandler(
        release_source=source, detector=FakeInstallMethodDetector(method), runner=runner
    )


async def test_check_reports_a_newer_release_and_the_detected_command() -> None:
    result = await checker(FakeReleaseSource(release())).handle(
        CheckForUpdateQuery(current="0.3.0")
    )
    assert (result.current, result.latest, result.update_available) == ("0.3.0", "0.4.0", True)
    assert result.upgrade_command == UV_COMMAND


async def test_check_falls_back_to_the_manual_command_when_undetected() -> None:
    result = await checker(FakeReleaseSource(release()), None).handle(
        CheckForUpdateQuery(current="0.3.0")
    )
    assert result.upgrade_command == MANUAL


async def test_check_without_a_release_is_not_an_error() -> None:
    result = await checker(FakeReleaseSource(None)).handle(CheckForUpdateQuery(current="0.3.0"))
    assert (result.latest, result.update_available, result.upgrade_command) == (None, False, None)


@pytest.mark.parametrize(
    "ignored", [release(prerelease=True), release(draft=True), release("nightly")]
)
async def test_check_treats_an_unusable_release_as_none(ignored: ReleaseInfoDTO) -> None:
    result = await checker(FakeReleaseSource(ignored)).handle(CheckForUpdateQuery(current="0.3.0"))
    assert (result.latest, result.update_available) == (None, False)


async def test_check_with_a_newer_install_is_not_an_update() -> None:
    result = await checker(FakeReleaseSource(release("v0.3.0"))).handle(
        CheckForUpdateQuery(current="0.9.0")
    )
    assert result.update_available is False


async def test_check_with_a_dev_version_is_unknown() -> None:
    result = await checker(FakeReleaseSource(release())).handle(
        CheckForUpdateQuery(current="0.0.0+unknown")
    )
    assert (result.latest, result.update_available) == ("0.4.0", None)


async def test_check_propagates_an_unavailable_source() -> None:
    source = FakeReleaseSource(error=ReleaseSourceUnavailableError("down"))
    with pytest.raises(ReleaseSourceUnavailableError):
        await checker(source).handle(CheckForUpdateQuery(current="0.3.0"))


async def test_apply_runs_the_detected_plan() -> None:
    runner = FakeInstallerRunner()
    result = await applier(FakeReleaseSource(release()), runner).handle(
        ApplyUpdateCommand(current="0.3.0")
    )
    assert [plan.command for plan in runner.plans] == [UV_COMMAND]
    assert (result.applied, result.current, result.latest) == (True, "0.3.0", "0.4.0")
    assert result.upgrade_command == UV_COMMAND


@pytest.mark.parametrize("latest", ["v0.3.0", "v0.2.0"])
async def test_apply_does_nothing_when_not_newer(latest: str) -> None:
    runner = FakeInstallerRunner()
    result = await applier(FakeReleaseSource(release(latest)), runner).handle(
        ApplyUpdateCommand(current="0.3.0")
    )
    assert (result.applied, runner.plans) == (False, [])


@pytest.mark.parametrize(
    "source", [FakeReleaseSource(None), FakeReleaseSource(release(draft=True))]
)
async def test_apply_without_a_release_fails(source: FakeReleaseSource) -> None:
    runner = FakeInstallerRunner()
    with pytest.raises(NoReleasePublishedError) as raised:
        await applier(source, runner).handle(ApplyUpdateCommand(current="0.3.0"))
    assert raised.value.error_code == "UPDATES_102_NO_RELEASE_PUBLISHED"
    assert raised.value.next_steps
    assert runner.plans == []


async def test_apply_refuses_a_dev_version() -> None:
    runner = FakeInstallerRunner()
    with pytest.raises(InvalidVersionError) as raised:
        await applier(FakeReleaseSource(release()), runner).handle(
            ApplyUpdateCommand(current="0.0.0+unknown")
        )
    assert MANUAL in raised.value.next_steps[0]
    assert runner.plans == []


async def test_apply_refuses_an_undetected_installer_with_the_manual_command() -> None:
    runner = FakeInstallerRunner()
    with pytest.raises(InstallerNotDetectedError) as raised:
        await applier(FakeReleaseSource(release()), runner, None).handle(
            ApplyUpdateCommand(current="0.3.0")
        )
    assert raised.value.error_code == "UPDATES_101_INSTALLER_NOT_DETECTED"
    assert any(MANUAL in step for step in raised.value.next_steps)
    assert runner.plans == []


async def test_apply_propagates_a_failed_install() -> None:
    runner = FakeInstallerRunner(error=UpgradeFailedError("boom"))
    with pytest.raises(UpgradeFailedError):
        await applier(FakeReleaseSource(release()), runner).handle(
            ApplyUpdateCommand(current="0.3.0")
        )
