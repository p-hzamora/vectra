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


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["search", "--json"], "Missing argument 'name'."),
        (["sync", "demo", "root", "--bogus", "--json"], "No such option: --bogus"),
        (["search", "demo", "q", "--top-k", "x", "--json"], "Invalid value"),
    ],
)
def test_usage_error_with_json_is_an_envelope(
    capsys: pytest.CaptureFixture[str], argv: list[str], message: str
) -> None:
    assert run(argv) == 2
    captured = capsys.readouterr()
    error = json.loads(captured.out)["error"]
    assert error["code"] == "INTERFACE_004_USAGE_ERROR"
    assert message in error["message"]
    assert error["next_steps"]
    assert captured.err == ""


def test_usage_error_without_json_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["search"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Usage:" in captured.err
    assert "Missing argument 'name'" in captured.err


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


def test_config_init_writes_the_template_once(
    capsys: pytest.CaptureFixture[str], isolated_home: Path
) -> None:
    env_file: Path = isolated_home / "config" / "vectra" / ".env"
    assert run(["config", "init", "--json"]) == 0
    assert _json(capsys)["result"] == {"env_file": str(env_file), "overwritten": False}
    assert "# VECTRA_DATA_DIR=" in env_file.read_text(encoding="utf-8")
    assert run(["config", "show"]) == 0
    assert "missing" not in capsys.readouterr().out

    assert run(["config", "init", "--json"]) == 1
    assert _json(capsys)["error"]["code"] == "CONFIGURATION_101_ENV_FILE_EXISTS"

    env_file.write_text("custom\n", encoding="utf-8")
    assert run(["config", "init", "--force"]) == 0
    assert capsys.readouterr().out == f"overwrote {env_file}\n"
    assert "custom" not in env_file.read_text(encoding="utf-8")


def test_config_init_honours_env_file(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    target: Path = tmp_path / "nested" / "work.env"
    assert run(["--env-file", str(target), "config", "init"]) == 0
    assert target.is_file()
    assert capsys.readouterr().out == f"wrote {target}\n"


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


def test_help_epilog_says_groups_take_json_on_their_subcommands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(["--help"]) == 0
    out = " ".join(capsys.readouterr().out.split())
    assert "command groups" in out
    assert "vectra collections list --json" in out


@pytest.mark.parametrize("group", ["collections", "config", "skills"])
def test_json_on_a_group_is_a_usage_error_pointing_at_its_subcommands(
    capsys: pytest.CaptureFixture[str], group: str
) -> None:
    assert run([group, "--json"]) == 2
    captured = capsys.readouterr()
    error = json.loads(captured.out)["error"]
    assert error["code"] == "INTERFACE_004_USAGE_ERROR"
    assert "command group" in error["next_steps"][0]
    assert f"vectra {group} " in error["next_steps"][0]
    assert captured.err == ""


def test_json_on_a_subcommand_of_a_group_works(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["collections", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
