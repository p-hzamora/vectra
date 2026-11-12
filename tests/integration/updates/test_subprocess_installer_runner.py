"""The runner executes an argv list with captured output; here the argv is a harmless Python one-liner."""

import sys
from pathlib import Path

import pytest

from vectra.bounded_context.updates.domain.value_objects import UpgradePlan
from vectra.bounded_context.updates.infrastructure.outbound.installer import (
    SubprocessInstallerRunnerAdapter,
)
from vectra.exceptions import UpgradeFailedError

pytestmark = pytest.mark.integration


def plan(code: str) -> UpgradePlan:
    return UpgradePlan(argv=(sys.executable, "-c", code))


def test_success_returns_quietly(capsys: pytest.CaptureFixture[str]) -> None:
    SubprocessInstallerRunnerAdapter().run(plan("print('installed')"))
    assert capsys.readouterr().out == ""  # captured, so it cannot corrupt --json output


def test_nonzero_exit_carries_the_stderr_tail() -> None:
    code = (
        "import sys\n"
        + "sys.stderr.write('\\n'.join(f'line {n}' for n in range(100)))\nsys.exit(3)"
    )
    with pytest.raises(UpgradeFailedError) as raised:
        SubprocessInstallerRunnerAdapter().run(plan(code))
    error = raised.value
    assert error.error_code == "UPDATES_202_UPGRADE_FAILED"
    assert error.metadata["exit_code"] == 3
    tail = error.metadata["stderr_tail"]
    assert isinstance(tail, str)
    assert "line 99" in tail
    assert "line 0\n" not in tail
    assert error.next_steps


def test_a_missing_program_is_an_upgrade_failure() -> None:
    with pytest.raises(UpgradeFailedError) as raised:
        SubprocessInstallerRunnerAdapter().run(UpgradePlan(argv=("/nonexistent/vectra-installer",)))
    assert raised.value.metadata["command"] == "/nonexistent/vectra-installer"


def test_arguments_are_never_interpreted_by_a_shell(tmp_path: Path) -> None:
    marker = tmp_path / "pwned"
    hostile = f"x; touch {marker}"
    SubprocessInstallerRunnerAdapter().run(
        UpgradePlan(argv=(sys.executable, "-c", "import sys", hostile))
    )
    assert not marker.exists()
