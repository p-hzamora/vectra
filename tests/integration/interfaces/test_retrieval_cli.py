"""The retrieval commands: JSON envelope, text output and exit codes."""

import json
import shutil
from pathlib import Path

import pytest

from tests.support.retrieval_fakes import FakeEmbedder
from vectra.interfaces.cli import bootstrap, run

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def fake_embedder(monkeypatch: pytest.MonkeyPatch) -> FakeEmbedder:
    embedder = FakeEmbedder()
    monkeypatch.setattr(bootstrap, "build_embedder", lambda environment: embedder)
    monkeypatch.setenv("VECTRA_SYNC_MAX_RETRIES", "0")
    return embedder


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    folder = tmp_path / "docs"
    (folder / "sub").mkdir(parents=True)
    (folder / "cats.md").write_text("# Cats\nfelines purr and hunt mice", encoding="utf-8")
    (folder / "sub" / "dogs.md").write_text("# Dogs\ncanines bark and fetch", encoding="utf-8")
    return folder


def _envelope(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    return json.loads(capsys.readouterr().out)


def _result(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    result = _envelope(capsys)["result"]
    assert isinstance(result, dict)
    return result


def _error(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    envelope = _envelope(capsys)
    assert envelope["ok"] is False
    error = envelope["error"]
    assert isinstance(error, dict)
    return error


def test_sync_indexes_and_a_second_run_changes_nothing(
    capsys: pytest.CaptureFixture[str], docs: Path
) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    first = _result(capsys)
    assert first["added"] == ["cats.md", "sub/dogs.md"]
    assert first["created"] is True
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    second = _result(capsys)
    assert (second["added"], second["unchanged"], second["created"]) == ([], 2, False)


def test_sync_dry_run_writes_nothing(capsys: pytest.CaptureFixture[str], docs: Path) -> None:
    assert run(["sync", "notes", str(docs), "--dry-run", "--json"]) == 0
    assert _result(capsys)["dry_run"] is True
    assert run(["collections", "list", "--json"]) == 0
    assert _result(capsys)["collections"] == []


def test_sync_text_output(capsys: pytest.CaptureFixture[str], docs: Path) -> None:
    assert run(["sync", "notes", str(docs)]) == 0
    out = capsys.readouterr().out
    assert "collection notes (new)" in out
    assert "add 2" in out


def test_sync_text_output_for_a_dry_run(capsys: pytest.CaptureFixture[str], docs: Path) -> None:
    assert run(["sync", "notes", str(docs), "--dry-run"]) == 0
    assert "[dry run]" in capsys.readouterr().out


def test_sync_include_and_exclude(capsys: pytest.CaptureFixture[str], docs: Path) -> None:
    assert run(["sync", "notes", str(docs), "--exclude", "sub/**", "--json"]) == 0
    assert _result(capsys)["added"] == ["cats.md"]


def test_sync_with_a_failing_file_reports_it_and_exits_1(
    capsys: pytest.CaptureFixture[str], docs: Path
) -> None:
    (docs / "bad.md").write_bytes(b"\xff\xfe\x00")
    assert run(["sync", "notes", str(docs), "--json"]) == 1
    result = _result(capsys)
    assert result["added"] == ["cats.md", "sub/dogs.md"]
    failed = result["failed"]
    assert isinstance(failed, list)
    assert failed[0] == {
        "path": "bad.md",
        "code": "RETRIEVAL_203_DOCUMENT_UNREADABLE",
        "message": failed[0]["message"],
        "attempts": 1,
    }


def test_sync_text_output_lists_failures_and_warnings(
    capsys: pytest.CaptureFixture[str], docs: Path
) -> None:
    (docs / "bad.md").write_bytes(b"\xff\xfe\x00")
    (docs / "fm.md").write_text("---\ntitle: [oops\n---\nbody", encoding="utf-8")
    assert run(["sync", "notes", str(docs)]) == 1
    out = capsys.readouterr().out
    assert "failed bad.md [RETRIEVAL_203_DOCUMENT_UNREADABLE] after 1 attempt(s)" in out
    assert "warning: fm.md: malformed frontmatter" in out


def test_sync_of_a_missing_root_is_201_and_exit_1(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    assert run(["sync", "notes", str(tmp_path / "missing"), "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_102_SOURCE_ROOT_INVALID"


def test_sync_of_another_root_is_102(
    capsys: pytest.CaptureFixture[str], docs: Path, tmp_path: Path
) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    capsys.readouterr()
    other = tmp_path / "other"
    other.mkdir()
    assert run(["sync", "notes", str(other), "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_102_SOURCE_ROOT_INVALID"


def test_sync_with_another_model_is_003(
    capsys: pytest.CaptureFixture[str],
    docs: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    capsys.readouterr()
    other = FakeEmbedder(model_id="other-model")
    monkeypatch.setattr(bootstrap, "build_embedder", lambda environment: other)
    assert run(["sync", "notes", str(docs), "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_003_INDEX_PROFILE_MISMATCH"


def test_mass_delete_needs_the_flag(capsys: pytest.CaptureFixture[str], docs: Path) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    capsys.readouterr()
    (docs / "cats.md").unlink()
    (docs / "sub" / "dogs.md").unlink()
    assert run(["sync", "notes", str(docs), "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_103_MASS_DELETE_REFUSED"
    assert run(["sync", "notes", str(docs), "--dry-run", "--json"]) == 0
    dry = _result(capsys)
    assert dry["deleted"] == ["cats.md", "sub/dogs.md"]
    assert "--allow-mass-delete" in dry["warnings"][0]
    assert run(["sync", "notes", str(docs), "--allow-mass-delete", "--json"]) == 0
    assert _result(capsys)["deleted"] == ["cats.md", "sub/dogs.md"]


def test_search_returns_ranked_documents(capsys: pytest.CaptureFixture[str], docs: Path) -> None:
    run(["sync", "notes", str(docs), "--json"])
    capsys.readouterr()
    assert run(["search", "notes", "felines purr hunt mice", "--top-k", "1", "--json"]) == 0
    result = _result(capsys)
    hits = result["hits"]
    assert isinstance(hits, list)
    assert [hit["path"] for hit in hits] == ["cats.md"]
    assert hits[0]["heading_path"] == ["Cats"]


def test_search_hit_json_shape_is_stable(capsys: pytest.CaptureFixture[str], docs: Path) -> None:
    """The contract noesis' vector adapter relies on."""
    run(["sync", "notes", str(docs), "--json"])
    capsys.readouterr()
    assert run(["search", "notes", "felines purr", "--top-k", "2", "--json"]) == 0
    envelope = _envelope(capsys)
    assert envelope["ok"] is True
    result = envelope["result"]
    assert isinstance(result, dict)
    assert set(result) == {"collection", "query", "hits"}
    hits = result["hits"]
    assert isinstance(hits, list)
    assert [hit["rank"] for hit in hits] == [1, 2]
    for hit in hits:
        assert set(hit) == {"rank", "path", "score", "heading_path", "snippet", "chunk_id"}
        assert isinstance(hit["score"], float)
        assert 0.0 <= hit["score"] <= 1.0
    assert hits[0]["score"] >= hits[1]["score"]


def test_sync_include_py_then_search_finds_a_function(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    code = tmp_path / "code"
    code.mkdir()
    (code / "pets.py").write_text(
        "def feed_cat():\n    return 'felines purr'\n\n\ndef walk_dog():\n    return 'canines bark'\n",
        encoding="utf-8",
    )
    assert run(["sync", "code", str(code), "--include", "**/*.py", "--json"]) == 0
    assert _result(capsys)["added"] == ["pets.py"]
    assert run(["search", "code", "def walk_dog canines bark", "--top-k", "1", "--json"]) == 0
    hits = _result(capsys)["hits"]
    assert isinstance(hits, list)
    assert hits[0]["path"] == "pets.py"
    assert hits[0]["heading_path"] == ["pets", "walk_dog"]


def test_search_text_output_and_filters(capsys: pytest.CaptureFixture[str], docs: Path) -> None:
    run(["sync", "notes", str(docs), "--json"])
    capsys.readouterr()
    assert run(["search", "notes", "canines bark", "--path-prefix", "sub/"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("sub/dogs.md")
    assert "[Dogs]" in out
    assert run(["search", "notes", "felines", "--min-score", "0.999", "--path-prefix", "sub/"]) == 0
    assert capsys.readouterr().out.strip() == "no results"


def test_search_errors(capsys: pytest.CaptureFixture[str], docs: Path) -> None:
    assert run(["search", "missing", "x", "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_101_COLLECTION_NOT_FOUND"
    run(["sync", "notes", str(docs), "--json"])
    capsys.readouterr()
    assert run(["search", "notes", "x", "--top-k", "0", "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_004_INVALID_SEARCH_QUERY"


def test_collections_list_and_drop(capsys: pytest.CaptureFixture[str], docs: Path) -> None:
    assert run(["collections", "list"]) == 0
    assert capsys.readouterr().out.strip() == "no collections"
    run(["sync", "notes", str(docs), "--json"])
    capsys.readouterr()
    assert run(["collections", "list", "--json"]) == 0
    collections = _result(capsys)["collections"]
    assert isinstance(collections, list)
    assert collections[0]["name"] == "notes"
    assert (collections[0]["document_count"], collections[0]["chunk_count"]) == (2, 2)
    assert run(["collections", "list"]) == 0
    assert "notes  2 documents, 2 chunks" in capsys.readouterr().out
    assert run(["collections", "drop", "notes", "--yes"]) == 0
    assert capsys.readouterr().out.startswith("dropped notes")
    assert run(["collections", "list", "--json"]) == 0
    assert _result(capsys)["collections"] == []


def test_drop_without_yes_is_a_usage_error_and_deletes_nothing(
    capsys: pytest.CaptureFixture[str], docs: Path
) -> None:
    run(["sync", "notes", str(docs), "--json"])
    capsys.readouterr()
    assert run(["collections", "drop", "notes", "--json"]) == 2
    error = _error(capsys)
    assert error["code"] == "INTERFACE_002_CONFIRMATION_REQUIRED"
    assert error["next_steps"] == ["Run `vectra collections drop notes --yes`."]
    assert run(["collections", "list", "--json"]) == 0
    collections = _result(capsys)["collections"]
    assert isinstance(collections, list) and len(collections) == 1


def test_drop_unknown_collection_is_101(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["collections", "drop", "nope", "--yes", "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_101_COLLECTION_NOT_FOUND"


def test_invalid_collection_name_is_001(capsys: pytest.CaptureFixture[str], docs: Path) -> None:
    assert run(["sync", "Bad Name", str(docs), "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_001_INVALID_COLLECTION_NAME"


def test_invalid_retry_setting_is_a_configuration_error(
    capsys: pytest.CaptureFixture[str], docs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VECTRA_SYNC_MAX_RETRIES", "-1")
    assert run(["sync", "notes", str(docs), "--json"]) == 1
    error = _error(capsys)
    assert error["code"] == "CORE_001_INVALID_CONFIGURATION"
    assert any("SYNC_MAX_RETRIES" in str(problem) for problem in error["metadata"]["problems"])  # type: ignore[index, attr-defined]


def test_help_lists_the_new_commands(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["--help"]) == 0
    out = capsys.readouterr().out
    for command in ("sync", "search", "collections"):
        assert command in out


def test_rebuild_is_the_way_out_of_a_profile_mismatch(
    capsys: pytest.CaptureFixture[str], docs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    capsys.readouterr()
    other = FakeEmbedder(model_id="other-model")
    monkeypatch.setattr(bootstrap, "build_embedder", lambda environment: other)
    assert run(["sync", "notes", str(docs), "--json"]) == 1
    capsys.readouterr()
    assert run(["sync", "notes", str(docs), "--rebuild", "--json"]) == 0
    result = _result(capsys)
    assert (result["created"], result["added"]) == (True, ["cats.md", "sub/dogs.md"])
    assert run(["collections", "list", "--json"]) == 0
    collections = _result(capsys)["collections"]
    assert isinstance(collections, list)
    assert collections[0]["model_id"] == "other-model"


def test_rebuild_refuses_another_root_without_new_root(
    capsys: pytest.CaptureFixture[str], docs: Path, tmp_path: Path
) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    other = tmp_path / "other"
    other.mkdir()
    capsys.readouterr()
    assert run(["sync", "notes", str(other), "--rebuild", "--json"]) == 1
    error = _error(capsys)
    assert error["code"] == "RETRIEVAL_102_SOURCE_ROOT_INVALID"
    assert "--new-root" in error["next_steps"][0]  # type: ignore[index]


def test_new_root_without_rebuild_is_a_usage_error(
    capsys: pytest.CaptureFixture[str], docs: Path
) -> None:
    assert run(["sync", "notes", str(docs), "--new-root", "--json"]) == 2
    assert _error(capsys)["code"] == "INTERFACE_003_NEW_ROOT_REQUIRES_REBUILD"


def test_rebuild_with_new_root_rebinds_the_root(
    capsys: pytest.CaptureFixture[str], docs: Path, tmp_path: Path
) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    other = tmp_path / "other"
    other.mkdir()
    (other / "x.md").write_text("# X\nbody", encoding="utf-8")
    capsys.readouterr()
    assert run(["sync", "notes", str(other), "--rebuild", "--new-root", "--json"]) == 0
    assert _result(capsys)["added"] == ["x.md"]


def test_collections_check_flags_a_changed_model_and_search_refuses_it(
    capsys: pytest.CaptureFixture[str],
    docs: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    capsys.readouterr()
    assert run(["collections", "check", "--json"]) == 0
    assert _result(capsys)["in_sync"] is True
    other = FakeEmbedder(model_id="other-model")
    monkeypatch.setattr(bootstrap, "build_embedder", lambda environment: other)
    assert run(["collections", "check", "notes", "--json"]) == 1
    assert _result(capsys)["in_sync"] is False
    assert run(["search", "notes", "x", "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_003_INDEX_PROFILE_MISMATCH"


def test_sync_without_root_reuses_the_collection_root(
    capsys: pytest.CaptureFixture[str], docs: Path
) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    capsys.readouterr()
    assert run(["sync", "notes", "--json"]) == 0
    assert _result(capsys)["unchanged"] == 2
    assert run(["sync", "fresh", "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_102_SOURCE_ROOT_INVALID"


def test_check_fix_rebuilds_out_of_sync_collections(
    capsys: pytest.CaptureFixture[str],
    docs: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    capsys.readouterr()
    other = FakeEmbedder(model_id="other-model")
    monkeypatch.setattr(bootstrap, "build_embedder", lambda environment: other)
    assert run(["collections", "check", "--fix", "--json"]) == 2
    assert _error(capsys)["code"] == "INTERFACE_002_CONFIRMATION_REQUIRED"
    assert run(["collections", "check", "--fix", "--yes", "--json"]) == 0
    repaired = _result(capsys)["repaired"]
    assert isinstance(repaired, list)
    assert (repaired[0]["collection"], repaired[0]["created"]) == ("notes", True)
    assert run(["collections", "check", "--json"]) == 0
    assert _result(capsys)["in_sync"] is True


def test_check_fix_skips_a_collection_whose_root_is_gone(
    capsys: pytest.CaptureFixture[str],
    docs: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    capsys.readouterr()
    shutil.rmtree(docs)
    other = FakeEmbedder(model_id="other-model")
    monkeypatch.setattr(bootstrap, "build_embedder", lambda environment: other)
    assert run(["collections", "check", "--fix", "--yes", "--json"]) == 1
    result = _result(capsys)
    assert result["repaired"] == []
    assert result["skipped"][0]["name"] == "notes"  # type: ignore[index]
    assert run(["collections", "check", "--json"]) == 1


def test_verbose_reports_progress_on_stderr_and_keeps_stdout_clean(
    capsys: pytest.CaptureFixture[str], docs: Path
) -> None:
    assert run(["sync", "notes", str(docs), "--verbose", "--json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["ok"] is True
    assert "scanning" in captured.err
    assert "[2/2] added" in captured.err
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    "argv",
    [
        ["search", "notes", "", "--json"],
        ["search", "notes", "   ", "--json"],
        ["search", "notes", "x", "--top-k", "0", "--json"],
        ["search", "notes", "x", "--top-k", "101", "--json"],
        ["search", "notes", "x", "--min-score", "2", "--json"],
        ["search", "notes", "x", "--path-prefix", "../etc", "--json"],
    ],
)
def test_invalid_search_input_is_clean_json_with_next_steps(
    capsys: pytest.CaptureFixture[str], docs: Path, argv: list[str]
) -> None:
    run(["sync", "notes", str(docs), "--json"])
    capsys.readouterr()
    assert run(argv) == 1
    error = _error(capsys)
    assert error["code"] == "RETRIEVAL_004_INVALID_SEARCH_QUERY"
    assert error["next_steps"]


def test_search_of_a_missing_collection_is_clean_json_with_next_steps(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(["search", "missing", "x", "--json"]) == 1
    error = _error(capsys)
    assert error["code"] == "RETRIEVAL_101_COLLECTION_NOT_FOUND"
    assert error["next_steps"]


def test_an_unexpected_failure_is_clean_json_not_a_traceback(
    capsys: pytest.CaptureFixture[str], docs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(bootstrap, "build_retrieval", explode)
    assert run(["search", "notes", "x", "--json"]) == 1
    captured = capsys.readouterr()
    error = json.loads(captured.out)["error"]
    assert error["code"] == "APP_000_UNEXPECTED"
    assert "boom" in error["message"]
    assert error["next_steps"]
    assert "Traceback" not in captured.out + captured.err
    assert run(["search", "notes", "x"]) == 1
    assert "Traceback" not in capsys.readouterr().err
