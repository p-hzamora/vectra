"""FilesystemDocumentSourceAdapter against a real folder."""

import hashlib
from pathlib import Path

import pytest

from vectra.bounded_context.retrieval.domain.value_objects import SourcePath
from vectra.bounded_context.retrieval.infrastructure.outbound.source import (
    FilesystemDocumentSourceAdapter,
)
from vectra.exceptions import DocumentReadError, SourceRootInvalidError

pytestmark = pytest.mark.integration


async def _scan(root: Path, include: tuple[str, ...] = ("**/*.md",), exclude: tuple[str, ...] = ()):  # type: ignore[no-untyped-def]
    return [
        file async for file in FilesystemDocumentSourceAdapter().scan(str(root), include, exclude)
    ]


def _tree(root: Path) -> None:
    (root / "sub").mkdir(parents=True)
    (root / ".hidden").mkdir()
    (root / "a.md").write_text("alpha", encoding="utf-8")
    (root / "sub" / "b.md").write_text("beta", encoding="utf-8")
    (root / "sub" / "c.txt").write_text("gamma", encoding="utf-8")
    (root / ".hidden" / "secret.md").write_text("no", encoding="utf-8")


async def test_scan_matches_include_in_sorted_order_with_hashes(tmp_path: Path) -> None:
    _tree(tmp_path)
    files = await _scan(tmp_path)
    assert [file.path for file in files] == ["a.md", "sub/b.md"]
    assert files[0].content_hash == hashlib.sha256(b"alpha").hexdigest()
    assert files[0].size == 5


async def test_scan_skips_hidden_directories(tmp_path: Path) -> None:
    _tree(tmp_path)
    assert ".hidden/secret.md" not in [file.path for file in await _scan(tmp_path, ("**/*",))]


async def test_scan_skips_symlinked_files_and_directories(tmp_path: Path) -> None:
    _tree(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "x.md").write_text("x", encoding="utf-8")
    (tmp_path / "link.md").symlink_to(tmp_path / "a.md")
    (tmp_path / "linkdir").symlink_to(outside, target_is_directory=True)
    assert [file.path for file in await _scan(tmp_path)] == ["a.md", "sub/b.md"]


async def test_scan_applies_exclude(tmp_path: Path) -> None:
    _tree(tmp_path)
    assert [file.path for file in await _scan(tmp_path, exclude=("sub/**",))] == ["a.md"]


async def test_scan_of_missing_root_raises_201(tmp_path: Path) -> None:
    with pytest.raises(SourceRootInvalidError) as raised:
        await _scan(tmp_path / "missing")
    assert raised.value.error_code == "RETRIEVAL_102_SOURCE_ROOT_INVALID"


async def test_read_text_and_failures(tmp_path: Path) -> None:
    _tree(tmp_path)
    source = FilesystemDocumentSourceAdapter()
    assert await source.read_text(str(tmp_path), SourcePath(value="sub/b.md")) == "beta"
    with pytest.raises(DocumentReadError):
        await source.read_text(str(tmp_path), SourcePath(value="nope.md"))
    (tmp_path / "bin.md").write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(DocumentReadError) as raised:
        await source.read_text(str(tmp_path), SourcePath(value="bin.md"))
    assert raised.value.error_code == "RETRIEVAL_203_DOCUMENT_UNREADABLE"
