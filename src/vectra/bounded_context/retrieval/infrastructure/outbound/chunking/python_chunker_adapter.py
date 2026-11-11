"""Python chunker: one chunk per function, class and method, plus one for the module level."""

import ast
from pathlib import PurePosixPath

from vectra.bounded_context.retrieval.application.ports.chunking import IChunker
from vectra.bounded_context.retrieval.domain.value_objects import (
    ChunkContent,
    ChunkedDocument,
    HeadingPath,
    SourcePath,
)

CHUNKER_VERSION: str = "python-1"
CHARS_PER_TOKEN: int = 4
MAX_TOKENS: int = 400
MAX_CHARS: int = MAX_TOKENS * CHARS_PER_TOKEN

_Definition = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
_Unit = tuple[tuple[str, ...], str]


class PythonChunkerAdapter(IChunker):
    """Parses with `ast`; the heading path is (module, class, method) or (module, function).

    Each unit's text is its source including decorators and docstring. A class chunk holds the
    class header, docstring and class-level statements, not its methods. The module docstring,
    imports and top-level statements form one chunk with the path (module,). A unit longer than
    400 tokens (4 characters per token) is cut at line boundaries into pieces of at most that
    size, without overlap. Source that does not parse is split at blank lines under the same cap,
    with a warning.
    """

    @property
    def chunker_version(self) -> str:
        return CHUNKER_VERSION

    @property
    def extensions(self) -> tuple[str, ...]:
        return (".py",)

    def chunk(self, text: str, path: SourcePath) -> ChunkedDocument:
        module: str = PurePosixPath(path.value).stem
        source: str = text.replace("\r\n", "\n").replace("\r", "\n")
        packer: _CapPacker = _CapPacker()
        warnings: list[str] = []
        try:
            units: list[_Unit] = _UnitExtractor(source, module).units(ast.parse(source))
        except (SyntaxError, ValueError) as error:
            warnings.append(f"not valid Python ({error}); split at blank lines instead")
            units = [((module,), block) for block in packer.pack(self._blocks(source), "\n\n")]
        chunks: list[ChunkContent] = [
            ChunkContent(heading_path=HeadingPath(parts=parts), text=piece)
            for parts, unit in units
            for piece in packer.pack([unit], "\n")
            if piece.strip()
        ]
        return ChunkedDocument(chunks=tuple(chunks), warnings=tuple(warnings))

    @staticmethod
    def _blocks(source: str) -> list[str]:
        """Runs of non-blank lines, separated by blank lines."""
        blocks: list[str] = []
        current: list[str] = []
        for line in source.split("\n"):
            if line.strip():
                current.append(line)
            elif current:
                blocks.append("\n".join(current))
                current = []
        if current:
            blocks.append("\n".join(current))
        return blocks


class _UnitExtractor:
    """Turns a parsed module into `(heading path, text)` units."""

    def __init__(self, source: str, module: str) -> None:
        self._lines: list[str] = source.split("\n")
        self._module: str = module

    def units(self, tree: ast.Module) -> list[_Unit]:
        """The module-level chunk first, then each definition in order."""
        module_level: list[str] = []
        definitions: list[_Unit] = []
        for node in tree.body:
            if isinstance(node, _Definition):
                definitions.extend(self._definition_units(node, (self._module,)))
            else:
                module_level.append(self._segment(node))
        return [((self._module,), "\n".join(module_level)), *definitions]

    def _definition_units(self, node: _Definition, scope: tuple[str, ...]) -> list[_Unit]:
        """The unit of a function, or of a class followed by those of its members."""
        path: tuple[str, ...] = (*scope, node.name)
        if not isinstance(node, ast.ClassDef):
            return [(path, self._segment(node))]
        own: list[str] = self._lines[self._start(node) - 1 : self._start(node.body[0]) - 1]
        members: list[_Unit] = []
        for child in node.body:
            if isinstance(child, _Definition):
                members.extend(self._definition_units(child, path))
            else:
                own.append(self._segment(child))
        return [(path, "\n".join(own)), *members]

    def _segment(self, node: ast.stmt) -> str:
        """Source lines of `node`, decorators included."""
        return "\n".join(self._lines[self._start(node) - 1 : node.end_lineno or node.lineno])

    @staticmethod
    def _start(node: ast.stmt) -> int:
        """First line of `node`, counting its decorators."""
        if isinstance(node, _Definition):
            return min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])
        return node.lineno


class _CapPacker:
    """Joins parts into pieces of at most `MAX_CHARS`, cutting any longer part first."""

    def pack(self, parts: list[str], separator: str) -> list[str]:
        """Consecutive parts joined with `separator` while the piece fits."""
        pieces: list[str] = []
        current: str = ""
        for part in parts:
            for piece in [part] if len(part) <= MAX_CHARS else self._cut(part):
                candidate: str = f"{current}{separator}{piece}" if current else piece
                if len(candidate) <= MAX_CHARS:
                    current = candidate
                    continue
                if current:
                    pieces.append(current)
                current = piece
        if current:
            pieces.append(current)
        return pieces

    def _cut(self, part: str) -> list[str]:
        """Cut at line boundaries; a single oversized line is cut at the limit."""
        if "\n" in part:
            return self.pack(part.split("\n"), "\n")
        return [part[i : i + MAX_CHARS] for i in range(0, len(part), MAX_CHARS)]
