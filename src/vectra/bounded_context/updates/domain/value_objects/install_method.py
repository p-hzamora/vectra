"""How vectra was installed on this machine."""

from enum import StrEnum
from typing import Self

from pydantic import model_validator

from vectra.utils import FrozenObject


class InstallerKind(StrEnum):
    """The installers `install.sh` can use."""

    UV = "uv"
    PIPX = "pipx"
    VENV = "venv"


class InstallMethod(FrozenObject):
    """An install that can be upgraded in place.

    Attributes:
        kind: The installer that owns the install.
        python: Interpreter vectra runs on (`VENV` and `PIPX` only): the venv to upgrade, or the
            interpreter handed to `pipx --python` so the reinstall keeps a supported Python.
    """

    kind: InstallerKind
    python: str | None = None

    @model_validator(mode="after")
    def _venv_and_pipx_have_an_interpreter(self) -> Self:
        if self.kind in {InstallerKind.VENV, InstallerKind.PIPX} and not self.python:
            raise ValueError("a venv or pipx install needs its interpreter")
        return self
