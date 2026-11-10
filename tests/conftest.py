"""Shared fixtures: every test runs with an isolated configuration and data folder."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the XDG folders at `tmp_path` so no test reads or writes the real ones."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.delenv("VECTRA_DATA_DIR", raising=False)
    return tmp_path
