"""Install-method detection from the interpreter prefix, over temp folders."""

from pathlib import Path

import pytest

from vectra.bounded_context.updates.domain.value_objects import InstallerKind, InstallMethod
from vectra.bounded_context.updates.infrastructure.outbound.installer import (
    ProcessInstallMethodDetectorAdapter,
)

pytestmark = pytest.mark.integration


def detect(
    prefix: Path,
    home: Path,
    *,
    environ: dict[str, str] | None = None,
    platform: str = "linux",
    editable: bool = False,
) -> InstallMethod | None:
    return ProcessInstallMethodDetectorAdapter(
        prefix=prefix, home=home, environ=environ or {}, platform=platform, editable=editable
    ).detect()


def test_uv_tool(tmp_path: Path) -> None:
    prefix = tmp_path / ".local" / "share" / "uv" / "tools" / "vectra"
    assert detect(prefix, tmp_path) == InstallMethod(kind=InstallerKind.UV)


def test_pipx(tmp_path: Path) -> None:
    prefix = tmp_path / ".local" / "share" / "pipx" / "venvs" / "vectra"
    assert detect(prefix, tmp_path) == InstallMethod(kind=InstallerKind.PIPX)


def test_private_venv_under_the_default_home(tmp_path: Path) -> None:
    prefix = tmp_path / ".local" / "share" / "vectra" / "venv"
    assert detect(prefix, tmp_path) == InstallMethod(
        kind=InstallerKind.VENV, python=str(prefix / "bin" / "python")
    )


def test_private_venv_under_vectra_home(tmp_path: Path) -> None:
    custom = tmp_path / "elsewhere"
    prefix = custom / "venv"
    method = detect(prefix, tmp_path, environ={"VECTRA_HOME": str(custom)})
    assert method == InstallMethod(kind=InstallerKind.VENV, python=str(prefix / "bin" / "python"))


def test_an_unknown_prefix_is_undetected(tmp_path: Path) -> None:
    assert detect(tmp_path / "somewhere" / ".venv", tmp_path) is None


def test_a_checkout_named_like_a_tool_folder_is_not_a_uv_tool(tmp_path: Path) -> None:
    assert detect(tmp_path / "uv" / "tools" / "other", tmp_path) is None


def test_editable_installs_are_refused_even_inside_a_tool_folder(tmp_path: Path) -> None:
    prefix = tmp_path / ".local" / "share" / "uv" / "tools" / "vectra"
    assert detect(prefix, tmp_path, editable=True) is None


def test_windows_is_unsupported(tmp_path: Path) -> None:
    prefix = tmp_path / ".local" / "share" / "uv" / "tools" / "vectra"
    assert detect(prefix, tmp_path, platform="win32") is None


def test_tool_directories_from_the_environment_are_honoured(tmp_path: Path) -> None:
    prefix = tmp_path / "tools-here" / "vectra"
    method = detect(prefix, tmp_path, environ={"UV_TOOL_DIR": str(prefix.parent)})
    assert method == InstallMethod(kind=InstallerKind.UV)


def test_multiple_matches_are_ambiguous(tmp_path: Path) -> None:
    prefix = tmp_path / "pipx-home" / "venvs" / "vectra"
    environ = {"PIPX_HOME": str(tmp_path / "pipx-home"), "UV_TOOL_DIR": str(prefix.parent)}
    assert detect(prefix, tmp_path, environ=environ) is None
