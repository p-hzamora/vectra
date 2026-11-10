"""The retrieval commands: JSON envelope, text output and exit codes."""

import json
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
        "code": "RETRIEVAL_204_DOCUMENT_READ_FAILURE",
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
    assert "failed bad.md [RETRIEVAL_204_DOCUMENT_READ_FAILURE] after 1 attempt(s)" in out
    assert "warning: fm.md: malformed frontmatter" in out


def test_sync_of_a_missing_root_is_201_and_exit_1(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    assert run(["sync", "notes", str(tmp_path / "missing"), "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_201_SOURCE_ROOT_NOT_FOUND"


def test_sync_of_another_root_is_102(
    capsys: pytest.CaptureFixture[str], docs: Path, tmp_path: Path
) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    capsys.readouterr()
    other = tmp_path / "other"
    other.mkdir()
    assert run(["sync", "notes", str(other), "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_102_SOURCE_ROOT_MISMATCH"


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
    assert _error(capsys)["code"] == "RETRIEVAL_003_EMBEDDING_PROFILE_MISMATCH"


def test_mass_delete_needs_the_flag(capsys: pytest.CaptureFixture[str], docs: Path) -> None:
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    capsys.readouterr()
    (docs / "cats.md").unlink()
    (docs / "sub" / "dogs.md").unlink()
    assert run(["sync", "notes", str(docs), "--json"]) == 1
    assert _error(capsys)["code"] == "RETRIEVAL_103_MASS_DELETE_REFUSED"
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
