"""MarkdownChunkerAdapter on real Markdown."""

import pytest

from vectra.bounded_context.retrieval.domain.value_objects import SourcePath
from vectra.bounded_context.retrieval.infrastructure.outbound.chunking import (
    MarkdownChunkerAdapter,
)
from vectra.bounded_context.retrieval.infrastructure.outbound.chunking.markdown_chunker_adapter import (
    MAX_CHARS,
)

pytestmark = pytest.mark.integration

PATH = SourcePath(value="a.md")


def _chunk(text: str):  # type: ignore[no-untyped-def]
    return MarkdownChunkerAdapter().chunk(text, PATH)


def test_identity() -> None:
    chunker = MarkdownChunkerAdapter()
    assert chunker.chunker_version == "markdown-1"
    assert ".md" in chunker.extensions


def test_splits_by_headings_with_nested_paths() -> None:
    result = _chunk("intro\n\n# A\nalpha\n\n## B\nbeta\n\n# C\ngamma\n")
    assert [(c.heading_path.parts, c.text) for c in result.chunks] == [
        ((), "intro"),
        (("A",), "alpha"),
        (("A", "B"), "beta"),
        (("C",), "gamma"),
    ]


def test_headings_inside_code_fences_are_text() -> None:
    result = _chunk("# A\n```\n# not a heading\n```\n")
    assert len(result.chunks) == 1
    assert "# not a heading" in result.chunks[0].text


def test_heading_without_body_makes_no_chunk() -> None:
    assert [c.text for c in _chunk("# A\n# B\nbody").chunks] == ["body"]


def test_frontmatter_becomes_metadata_on_every_chunk() -> None:
    result = _chunk("---\ntitle: Hi\ntags: [x, y]\ndate: 2026-01-02\n---\n# A\none\n# B\ntwo\n")
    assert result.warnings == ()
    assert len(result.chunks) == 2
    for chunk in result.chunks:
        assert chunk.metadata == {"title": "Hi", "tags": ["x", "y"], "date": "2026-01-02"}


def test_malformed_frontmatter_gives_no_metadata_and_a_warning() -> None:
    result = _chunk("---\ntitle: [unclosed\n  - : :\n---\nbody text\n")
    assert [c.text for c in result.chunks] == ["body text"]
    assert result.chunks[0].metadata == {}
    assert len(result.warnings) == 1
    assert "malformed frontmatter" in result.warnings[0]


def test_non_mapping_frontmatter_warns() -> None:
    result = _chunk("---\n- a\n- b\n---\nbody")
    assert result.chunks[0].metadata == {}
    assert result.warnings == ("frontmatter is not a mapping and was ignored",)


def test_empty_frontmatter_and_unclosed_frontmatter() -> None:
    assert _chunk("---\n---\nbody").warnings == ()
    unclosed = _chunk("---\nnot closed\nbody")
    assert unclosed.warnings == ()
    assert "not closed" in unclosed.chunks[0].text


def test_empty_document_has_no_chunks() -> None:
    assert _chunk("").chunks == ()


def test_short_section_stays_whole() -> None:
    text = "p1\n\np2\n\np3"
    assert [c.text for c in _chunk(text).chunks] == [text]


def test_long_section_is_split_at_paragraphs_without_overlap() -> None:
    paragraphs = [f"{chr(65 + i)} " + "word " * 150 for i in range(6)]  # ~750 chars each
    pieces = [c.text for c in _chunk("# T\n" + "\n\n".join(paragraphs)).chunks]
    assert len(pieces) == 3
    assert all(len(piece) <= MAX_CHARS for piece in pieces)
    assert "\n\n".join(pieces) == "\n\n".join(p.strip() for p in paragraphs)


def test_a_single_400_token_plus_paragraph_is_cut_at_whitespace() -> None:
    paragraph = " ".join(["token"] * 600)  # 3599 chars ~ 900 tokens
    pieces = [c.text for c in _chunk(paragraph).chunks]
    assert len(pieces) == 3
    assert all(len(piece) <= MAX_CHARS for piece in pieces)
    assert " ".join(pieces) == paragraph


def test_a_word_longer_than_the_limit_is_hard_cut() -> None:
    pieces = [c.text for c in _chunk("x" * (MAX_CHARS * 2 + 5)).chunks]
    assert [len(piece) for piece in pieces] == [MAX_CHARS, MAX_CHARS, 5]


def test_blank_lines_inside_a_fence_do_not_split() -> None:
    code = "```\nfirst\n\nsecond\n```"
    filler = "\n\n".join(["filler " * 100] * 4)
    pieces = [c.text for c in _chunk(f"{filler}\n\n{code}").chunks]
    assert len(pieces) > 1
    assert any(code in piece for piece in pieces)
