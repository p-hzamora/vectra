"""Tells how vectra was installed from the interpreter it is running in."""

import json
import os
import sys
from collections.abc import Mapping
from importlib import metadata
from pathlib import Path

from vectra.bounded_context.updates.application.ports.installer import IInstallMethodDetector
from vectra.bounded_context.updates.domain.value_objects import InstallerKind, InstallMethod

_PACKAGE: str = "vectra"


def _is_editable() -> bool:
    """Whether the installed distribution points at a source tree (PEP 610 `direct_url.json`)."""
    try:
        text: str | None = metadata.distribution(_PACKAGE).read_text("direct_url.json")
    except metadata.PackageNotFoundError:
        return False
    if text is None:
        return False
    try:
        document: object = json.loads(text)
    except ValueError:
        return False
    info: object = document.get("dir_info") if isinstance(document, dict) else None
    return isinstance(info, dict) and info.get("editable") is True


class ProcessInstallMethodDetectorAdapter(IInstallMethodDetector):
    """Matches the running interpreter's prefix against the folders each installer uses.

    Args:
        prefix: Interpreter prefix (default `sys.prefix`).
        home: The user's home folder (default `Path.home()`).
        environ: Environment to read `VECTRA_HOME`, `UV_TOOL_DIR`, `PIPX_HOME` and
            `XDG_DATA_HOME` from (default `os.environ`).
        platform: Platform name (default `sys.platform`).
        editable: Whether the install is editable (default: read the package metadata).
    """

    def __init__(
        self,
        *,
        prefix: Path | None = None,
        home: Path | None = None,
        environ: Mapping[str, str] | None = None,
        platform: str | None = None,
        editable: bool | None = None,
    ) -> None:
        self._prefix: Path = prefix or Path(sys.prefix)
        self._home: Path = home or Path.home()
        self._environ: Mapping[str, str] = os.environ if environ is None else environ
        self._platform: str = platform or sys.platform
        self._editable: bool | None = editable

    def detect(self) -> InstallMethod | None:
        if self._platform.startswith("win"):
            return None
        if self._editable if self._editable is not None else _is_editable():
            return None
        found: list[InstallMethod] = []
        if self._is_uv_tool():
            found.append(InstallMethod(kind=InstallerKind.UV))
        if self._is_pipx_venv():
            found.append(InstallMethod(kind=InstallerKind.PIPX))
        if self._is_private_venv():
            found.append(
                InstallMethod(kind=InstallerKind.VENV, python=str(self._prefix / "bin" / "python"))
            )
        return found[0] if len(found) == 1 else None

    def _is_uv_tool(self) -> bool:
        tools: str | None = self._environ.get("UV_TOOL_DIR")
        parent: Path = self._prefix.parent
        return self._prefix.name == _PACKAGE and (
            (tools is not None and parent == Path(tools))
            or (parent.name == "tools" and parent.parent.name == "uv")
        )

    def _is_pipx_venv(self) -> bool:
        pipx_home: str | None = self._environ.get("PIPX_HOME")
        parent: Path = self._prefix.parent
        return self._prefix.name == _PACKAGE and (
            (pipx_home is not None and parent == Path(pipx_home) / "venvs")
            or (parent.name == "venvs" and parent.parent.name == "pipx")
        )

    def _is_private_venv(self) -> bool:
        """`install.sh` puts the venv at `$VECTRA_HOME/venv`, default `~/.local/share/vectra`."""
        base: Path = Path(
            self._environ.get("VECTRA_HOME") or self._home / ".local" / "share" / "vectra"
        )
        return self._prefix == base / "venv"
