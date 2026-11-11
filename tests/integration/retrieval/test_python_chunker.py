"""PythonChunkerAdapter on real Python source."""

import pytest

from vectra.bounded_context.retrieval.application.services import ChunkerResolver
from vectra.bounded_context.retrieval.domain.value_objects import SourcePath
from vectra.bounded_context.retrieval.infrastructure.outbound.chunking import (
    MarkdownChunkerAdapter,
    PythonChunkerAdapter,
)
from vectra.bounded_context.retrieval.infrastructure.outbound.chunking.python_chunker_adapter import (
    MAX_CHARS,
)

pytestmark = pytest.mark.integration

PATH = SourcePath(value="pkg/mod.py")


def _chunk(text: str):  # type: ignore[no-untyped-def]
    return PythonChunkerAdapter().chunk(text, PATH)


def _pairs(text: str) -> list[tuple[tuple[str, ...], str]]:
    return [(c.heading_path.parts, c.text) for c in _chunk(text).chunks]


def test_identity() -> None:
    chunker = PythonChunkerAdapter()
    assert chunker.chunker_version == "python-1"
    assert chunker.extensions == (".py",)


def test_one_chunk_per_top_level_function() -> None:
    assert _pairs("def a():\n    return 1\n\n\nasync def b():\n    return 2\n") == [
        (("mod", "a"), "def a():\n    return 1"),
        (("mod", "b"), "async def b():\n    return 2"),
    ]


def test_class_and_each_method_get_a_chunk() -> None:
    source = (
        "class Cat:\n"
        '    """A cat."""\n'
        "    legs = 4\n"
        "\n"
        "    def purr(self):\n"
        "        return 'purr'\n"
        "\n"
        "    def hunt(self):\n"
        "        return 'mouse'\n"
    )
    assert _pairs(source) == [
        (("mod", "Cat"), 'class Cat:\n    """A cat."""\n    legs = 4'),
        (("mod", "Cat", "purr"), "    def purr(self):\n        return 'purr'"),
        (("mod", "Cat", "hunt"), "    def hunt(self):\n        return 'mouse'"),
    ]


def test_nested_class_extends_the_path() -> None:
    paths = [parts for parts, _ in _pairs("class A:\n    class B:\n        def m(self): ...\n")]
    assert paths == [("mod", "A"), ("mod", "A", "B"), ("mod", "A", "B", "m")]


def test_decorators_are_part_of_the_chunk() -> None:
    source = "import functools\n\n\n@functools.cache\n@staticmethod\ndef f():\n    pass\n"
    assert _pairs(source)[1] == (
        ("mod", "f"),
        "@functools.cache\n@staticmethod\ndef f():\n    pass",
    )


def test_decorated_method_and_class_keep_decorators() -> None:
    source = "@final\nclass A:\n    @property\n    def p(self):\n        return 1\n"
    assert _pairs(source) == [
        (("mod", "A"), "@final\nclass A:"),
        (("mod", "A", "p"), "    @property\n    def p(self):\n        return 1"),
    ]


def test_module_docstring_imports_and_assignments_form_one_chunk_first() -> None:
    source = '"""Doc."""\nimport os\n\ndef f():\n    pass\n\nLIMIT = 3\n'
    assert _pairs(source) == [
        (("mod",), '"""Doc."""\nimport os\nLIMIT = 3'),
        (("mod", "f"), "def f():\n    pass"),
    ]


def test_long_function_is_cut_at_line_boundaries_without_overlap() -> None:
    body = [f"    x{i} = {i}  # " + "pad " * 20 for i in range(30)]
    unit = "\n".join(["def big():", *body])
    result = _chunk(unit + "\n")
    pieces = [c.text for c in result.chunks]
    assert len(pieces) > 1
    assert all(len(piece) <= MAX_CHARS for piece in pieces)
    assert all(c.heading_path.parts == ("mod", "big") for c in result.chunks)
    assert "\n".join(pieces) == unit


def test_syntax_error_falls_back_to_blank_line_blocks_with_a_warning() -> None:
    result = _chunk("def broken(:\n    pass\n\n\nx = 1\n")
    assert [(c.heading_path.parts, c.text) for c in result.chunks] == [
        (("mod",), "def broken(:\n    pass\n\nx = 1")
    ]
    assert len(result.warnings) == 1
    assert "not valid Python" in result.warnings[0]


def test_fallback_respects_the_cap() -> None:
    blocks = "\n\n".join(["word " * 150 for _ in range(6)])
    result = _chunk("def (:\n" + blocks)
    assert len(result.chunks) > 1
    assert all(len(c.text) <= MAX_CHARS for c in result.chunks)


def test_empty_file_has_no_chunks() -> None:
    result = _chunk("")
    assert result.chunks == ()
    assert result.warnings == ()
    assert _chunk("\n\n").chunks == ()


def test_output_is_deterministic() -> None:
    source = "import os\n\nclass A:\n    def m(self):\n        pass\n\ndef f():\n    pass\n"
    assert _chunk(source) == _chunk(source)


def test_resolver_picks_it_for_py_and_markdown_for_md() -> None:
    python, markdown = PythonChunkerAdapter(), MarkdownChunkerAdapter()
    resolver = ChunkerResolver([markdown, python])
    assert resolver.resolve(SourcePath(value="a/B.PY")) is python
    assert resolver.resolve(SourcePath(value="a.md")) is markdown


def test_a_line_longer_than_the_limit_is_hard_cut() -> None:
    pieces = [c.text for c in _chunk("x = '" + "y" * (MAX_CHARS * 2) + "'\n").chunks]
    assert [len(piece) for piece in pieces] == [MAX_CHARS, MAX_CHARS, 6]
