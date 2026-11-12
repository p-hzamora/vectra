"""`vectra update` through `run(argv)` with fake ports: no network, no installer."""

import json

import pytest

from tests.support.updates_fakes import (
    FakeInstallerRunner,
    FakeInstallMethodDetector,
    FakeReleaseSource,
)
from vectra.bounded_context.updates.application.dtos import ReleaseInfoDTO
from vectra.bounded_context.updates.domain.value_objects import InstallerKind, InstallMethod
from vectra.exceptions import ReleaseSourceUnavailableError, UpgradeFailedError
from vectra.interfaces.cli import bootstrap, run
from vectra.interfaces.cli.commands import update_commands

pytestmark = pytest.mark.integration

UV_COMMAND = (
    "uv tool install --force --python '>=3.14' git+https://github.com/p-hzamora/vectra@v0.4.0"
)
MANUAL = "curl -LsSf https://raw.githubusercontent.com/p-hzamora/vectra/main/install.sh | VECTRA_REF=v0.4.0 sh"


class Wiring:
    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.source = FakeReleaseSource(ReleaseInfoDTO(tag_name="v0.4.0"))
        self.detector = FakeInstallMethodDetector(InstallMethod(kind=InstallerKind.UV))
        self.runner = FakeInstallerRunner()
        real = bootstrap.build_updates
        monkeypatch.setattr(update_commands, "__version__", "0.3.0")
        monkeypatch.setattr(
            bootstrap,
            "build_updates",
            lambda: real(release_source=self.source, detector=self.detector, runner=self.runner),
        )


@pytest.fixture
def wiring(monkeypatch: pytest.MonkeyPatch) -> Wiring:
    return Wiring(monkeypatch)


def envelope(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    return json.loads(capsys.readouterr().out)


@pytest.mark.parametrize("argv", [["update", "--json"], ["update", "--check", "--json"]])
def test_check_is_the_default(
    wiring: Wiring, capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    assert run(argv) == 0
    assert envelope(capsys)["result"] == {
        "current": "0.3.0",
        "latest": "0.4.0",
        "update_available": True,
        "upgrade_command": UV_COMMAND,
    }
    assert wiring.runner.plans == []


def test_check_text(wiring: Wiring, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["update"]) == 0
    out = capsys.readouterr().out
    assert "0.3.0" in out
    assert "0.4.0" in out
    assert UV_COMMAND in out


def test_check_without_any_release_exits_zero(
    wiring: Wiring, capsys: pytest.CaptureFixture[str]
) -> None:
    wiring.source.release = None
    assert run(["update", "--json"]) == 0
    assert envelope(capsys)["result"] == {
        "current": "0.3.0",
        "latest": None,
        "update_available": False,
        "upgrade_command": None,
    }


def test_check_with_an_unknown_installer_shows_the_manual_command(
    wiring: Wiring, capsys: pytest.CaptureFixture[str]
) -> None:
    wiring.detector.method = None
    assert run(["update", "--json"]) == 0
    result = envelope(capsys)["result"]
    assert isinstance(result, dict)
    assert result["upgrade_command"] == MANUAL


def test_check_with_the_release_source_down_is_exit_1(
    wiring: Wiring, capsys: pytest.CaptureFixture[str]
) -> None:
    wiring.source.error = ReleaseSourceUnavailableError("offline", next_steps=["Retry."])
    assert run(["update", "--json"]) == 1
    error = envelope(capsys)["error"]
    assert isinstance(error, dict)
    assert error["code"] == "UPDATES_201_RELEASE_SOURCE_UNAVAILABLE"
    assert error["next_steps"] == ["Retry."]


def test_apply_without_yes_is_refused_before_any_network_call(
    wiring: Wiring, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(["update", "--apply", "--json"]) == 2
    error = envelope(capsys)["error"]
    assert isinstance(error, dict)
    assert error["code"] == "INTERFACE_002_CONFIRMATION_REQUIRED"
    assert "vectra update --apply --yes" in " ".join(error["next_steps"])
    assert (wiring.source.calls, wiring.runner.plans) == (0, [])


def test_check_with_apply_is_a_usage_error(
    wiring: Wiring, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(["update", "--check", "--apply", "--yes", "--json"]) == 2
    error = envelope(capsys)["error"]
    assert isinstance(error, dict)
    assert error["code"] == "INTERFACE_004_USAGE_ERROR"
    assert error["next_steps"]
    assert wiring.runner.plans == []


def test_apply_yes_runs_the_plan_and_points_at_collections_check(
    wiring: Wiring, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(["update", "--apply", "--yes", "--json"]) == 0
    result = envelope(capsys)["result"]
    assert isinstance(result, dict)
    assert (result["applied"], result["current"], result["latest"]) == (True, "0.3.0", "0.4.0")
    assert result["upgrade_command"] == UV_COMMAND
    assert any("vectra collections check" in step for step in result["next_steps"])  # type: ignore[attr-defined]
    assert [plan.command for plan in wiring.runner.plans] == [UV_COMMAND]


def test_apply_when_up_to_date_does_nothing(
    wiring: Wiring, capsys: pytest.CaptureFixture[str]
) -> None:
    wiring.source.release = ReleaseInfoDTO(tag_name="v0.3.0")
    assert run(["update", "--apply", "--yes", "--json"]) == 0
    result = envelope(capsys)["result"]
    assert isinstance(result, dict)
    assert result["applied"] is False
    assert result["next_steps"] == []
    assert wiring.runner.plans == []


def test_apply_text(wiring: Wiring, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["update", "--apply", "--yes"]) == 0
    out = capsys.readouterr().out
    assert "updated 0.3.0 -> 0.4.0" in out
    assert "vectra collections check" in out


def test_apply_with_an_undetected_installer_refuses(
    wiring: Wiring, capsys: pytest.CaptureFixture[str]
) -> None:
    wiring.detector.method = None
    assert run(["update", "--apply", "--yes", "--json"]) == 1
    error = envelope(capsys)["error"]
    assert isinstance(error, dict)
    assert error["code"] == "UPDATES_101_INSTALLER_NOT_DETECTED"
    assert MANUAL in " ".join(error["next_steps"])
    assert wiring.runner.plans == []


def test_apply_when_the_installer_fails_is_exit_1(
    wiring: Wiring, capsys: pytest.CaptureFixture[str]
) -> None:
    wiring.runner.error = UpgradeFailedError("pip failed", {"stderr_tail": "boom"})
    assert run(["update", "--apply", "--yes", "--json"]) == 1
    error = envelope(capsys)["error"]
    assert isinstance(error, dict)
    assert error["code"] == "UPDATES_202_UPGRADE_FAILED"
    assert error["metadata"] == {"stderr_tail": "boom"}


def test_apply_without_a_release_fails(wiring: Wiring, capsys: pytest.CaptureFixture[str]) -> None:
    wiring.source.release = None
    assert run(["update", "--apply", "--yes", "--json"]) == 1
    error = envelope(capsys)["error"]
    assert isinstance(error, dict)
    assert error["code"] == "UPDATES_102_NO_RELEASE_PUBLISHED"
