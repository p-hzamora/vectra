"""The CLI contract: JSON envelope, text output and exit codes."""

import json
from pathlib import Path

import pytest

from vectra.interfaces.cli import run

pytestmark = pytest.mark.integration


def _json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    return json.loads(capsys.readouterr().out)


def test_version_prints_program_name(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["--version"]) == 0
    assert capsys.readouterr().out.startswith("vectra ")


def test_unknown_command_is_a_usage_error() -> None:
    assert run(["nope"]) == 2


def test_config_show_reports_default_locations(
    capsys: pytest.CaptureFixture[str], isolated_home: Path
) -> None:
    assert run(["config", "show", "--json"]) == 0
    result = _json(capsys)["result"]
    assert result == {
        "env_file": str(isolated_home / "config" / "vectra" / ".env"),
        "env_file_exists": False,
        "data_dir": str(isolated_home / "data" / "vectra"),
    }


def test_config_show_reads_the_env_file(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    env_file: Path = tmp_path / "custom.env"
    env_file.write_text(f"VECTRA_DATA_DIR={tmp_path / 'index'}\n", encoding="utf-8")
    assert run(["--env-file", str(env_file), "config", "show"]) == 0
    assert f"data dir: {tmp_path / 'index'}" in capsys.readouterr().out


def test_skills_get_returns_the_vectra_guide(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["skills", "get", "vectra", "--json"]) == 0
    result = _json(capsys)["result"]
    assert isinstance(result, dict)
    assert result["title"] == "vectra: guide for agents"


def test_skills_get_unknown_guide_is_a_usage_error_with_next_steps(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(["skills", "get", "missing", "--json"]) == 2
    envelope = _json(capsys)
    assert envelope["ok"] is False
    error = envelope["error"]
    assert isinstance(error, dict)
    assert error["code"] == "INTERFACE_001_SKILL_GUIDE_NOT_FOUND"
    assert error["metadata"] == {"available": ["vectra"]}
