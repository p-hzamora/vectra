"""Markdown chunker: split by headings, then by paragraphs when a section is too long."""

import json
import re
from typing import Any

import yaml

from vectra.bounded_context.retrieval.application.ports.chunking import IChunker
from vectra.bounded_context.retrieval.domain.value_objects import (
    ChunkContent,
    ChunkedDocument,
    HeadingPath,
    SourcePath,
)
from vectra.shared_kernel.domain import JsonObject

CHUNKER_VERSION: str = "markdown-1"
CHARS_PER_TOKEN: int = 4
MAX_TOKENS: int = 400
MAX_CHARS: int = MAX_TOKENS * CHARS_PER_TOKEN
_HEADING: re.Pattern[str] = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t#]*$")
_FENCE: re.Pattern[str] = re.compile(r"^\s*(```|~~~)")


class MarkdownChunkerAdapter(IChunker):
    """Frontmatter becomes chunk metadata; malformed frontmatter is dropped with a warning.

    A section longer than 400 tokens (4 characters per token) is cut at paragraph boundaries
    into pieces of at most that size, without overlap; a single longer paragraph is cut at
    whitespace.
    """

    @property
    def chunker_version(self) -> str:
        return CHUNKER_VERSION

    @property
    def extensions(self) -> tuple[str, ...]:
        return (".md", ".markdown")

    def chunk(self, text: str, path: SourcePath) -> ChunkedDocument:
        metadata, body, warnings = _split_frontmatter(text)
        chunks: list[ChunkContent] = []
        for heading_path, section in _sections(body):
            chunks.extend(
                ChunkContent(
                    heading_path=HeadingPath(parts=heading_path), text=piece, metadata=metadata
                )
                for piece in _pieces(section)
            )
        return ChunkedDocument(chunks=tuple(chunks), warnings=tuple(warnings))


def _split_frontmatter(text: str) -> tuple[JsonObject, str, list[str]]:
    """`(metadata, body, warnings)`; the frontmatter block is removed from the body."""
    lines: list[str] = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, []
    end: int | None = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, text, []
    body: str = "\n".join(lines[end + 1 :])
    try:
        loaded: Any = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError:
        return {}, body, ["malformed frontmatter ignored (no metadata for this document)"]
    if loaded is None:
        return {}, body, []
    if not isinstance(loaded, dict):
        return {}, body, ["frontmatter is not a mapping and was ignored"]
    metadata: JsonObject = json.loads(json.dumps(loaded, default=str))
    return metadata, body, []


def _sections(body: str) -> list[tuple[tuple[str, ...], str]]:
    """`(heading path, text)` for each heading section; headings in code fences are text."""
    sections: list[tuple[tuple[str, ...], str]] = []
    stack: list[tuple[int, str]] = []
    current: list[str] = []
    current_path: tuple[str, ...] = ()
    in_fence: bool = False

    def flush() -> None:
        text: str = "\n".join(current).strip()
        if text:
            sections.append((current_path, text))
        current.clear()

    for line in body.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
        match: re.Match[str] | None = None if in_fence else _HEADING.match(line)
        if match is None:
            current.append(line)
            continue
        flush()
        level: int = len(match.group(1))
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, match.group(2).strip()))
        current_path = tuple(title for _, title in stack)
    flush()
    return sections


def _pieces(section: str) -> list[str]:
    """The section whole when it fits, else paragraphs packed up to `MAX_CHARS`."""
    if len(section) <= MAX_CHARS:
        return [section]
    pieces: list[str] = []
    current: str = ""
    for paragraph in _paragraphs(section):
        for part in _cut(paragraph):
            candidate: str = f"{current}\n\n{part}" if current else part
            if len(candidate) <= MAX_CHARS:
                current = candidate
                continue
            if current:
                pieces.append(current)
            current = part
    if current:
        pieces.append(current)
    return pieces


def _paragraphs(section: str) -> list[str]:
    """Blocks separated by blank lines; blank lines inside code fences do not separate."""
    paragraphs: list[str] = []
    current: list[str] = []
    in_fence: bool = False
    for line in section.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
        if not line.strip() and not in_fence:
            if current:
                paragraphs.append("\n".join(current).strip())
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append("\n".join(current).strip())
    return paragraphs


def _cut(paragraph: str) -> list[str]:
    """Cut one oversized paragraph at whitespace into parts of at most `MAX_CHARS`."""
    parts: list[str] = []
    rest: str = paragraph
    while len(rest) > MAX_CHARS:
        cut: int = rest.rfind(" ", 0, MAX_CHARS)
        cut = cut if cut > 0 else MAX_CHARS
        parts.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        parts.append(rest)
    return parts
