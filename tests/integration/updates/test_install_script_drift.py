"""The commands `vectra update --apply` runs must not drift from the ones `install.sh` runs."""

import re
import shlex
from pathlib import Path

import pytest

from vectra.bounded_context.updates.domain.policies import REPO_URL, UpgradePlanPolicy
from vectra.bounded_context.updates.domain.value_objects import (
    InstallerKind,
    InstallMethod,
    ReleaseTag,
)

pytestmark = pytest.mark.integration

INSTALL_SH: Path = Path(__file__).resolve().parents[3] / "install.sh"
TAG: ReleaseTag = ReleaseTag.parse("v1.2.3")


def script_lines() -> list[str]:
    return [line.strip() for line in INSTALL_SH.read_text(encoding="utf-8").splitlines()]


def script_command(prefix: str) -> list[str]:
    """Tokens of the single line of install.sh starting with `prefix`."""
    lines = [line for line in script_lines() if line.startswith(prefix)]
    assert len(lines) == 1, prefix
    return shlex.split(lines[0])


def plan_tokens(method: InstallMethod) -> list[str]:
    return list(UpgradePlanPolicy().plan(method, TAG).argv)


def spec_free(tokens: list[str]) -> list[str]:
    """Drop the install spec and the `--python` choice, which install.sh resolves at run time."""
    cleaned: list[str] = []
    skip = False
    for token in tokens:
        if skip:
            skip = False
        elif token == "--python" and "$python" in tokens:
            skip = True
        elif token not in {"$spec", f"git+{REPO_URL}@{TAG}"}:
            cleaned.append(token)
    return cleaned


def test_repository_url_matches() -> None:
    assert f'REPO_URL="{REPO_URL}"' in script_lines()


def test_the_pinned_spec_has_the_shape_install_sh_builds() -> None:
    assert 'case "$VECTRA_SOURCE" in' in script_lines()
    assert any(
        line.endswith('spec="git+${VECTRA_SOURCE}@${VECTRA_REF}" ;;') for line in script_lines()
    )


def test_uv_command_matches() -> None:
    assert spec_free(plan_tokens(InstallMethod(kind=InstallerKind.UV))) == spec_free(
        script_command("uv tool install")
    )


def test_pipx_command_matches_apart_from_the_interpreter_choice() -> None:
    assert spec_free(plan_tokens(InstallMethod(kind=InstallerKind.PIPX))) == spec_free(
        script_command("pipx install")
    )


def test_venv_command_installs_the_same_spec_with_pip() -> None:
    script = script_command('"$VECTRA_HOME/venv/bin/python" -m pip install --quiet "$spec"')
    assert script[1:4] == ["-m", "pip", "install"]
    plan = plan_tokens(InstallMethod(kind=InstallerKind.VENV, python="/v/bin/python"))
    assert plan[1:4] == ["-m", "pip", "install"]
    assert plan[-1] == f"git+{REPO_URL}@{TAG}"


def test_the_manual_command_uses_the_script_ref_variable() -> None:
    assert re.search(r'VECTRA_REF="\$\{VECTRA_REF:-main\}"', INSTALL_SH.read_text(encoding="utf-8"))
    assert "VECTRA_REF=v1.2.3 sh" in UpgradePlanPolicy().manual_command(TAG)
