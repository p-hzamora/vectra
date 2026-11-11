"""SentenceTransformersEmbedderAdapter with a stub SDK; the real model sits behind `-m model`."""

import math
import os
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from vectra.bounded_context.retrieval.infrastructure.outbound.embedding import (
    SentenceTransformersEmbedderAdapter,
)
from vectra.bounded_context.retrieval.infrastructure.outbound.embedding.sentence_transformers_embedder_adapter import (
    BGE_QUERY_PREFIX,
)
from vectra.exceptions import EmbeddingModelError
from vectra.interfaces.cli import run


class _StubModel:
    loads: int = 0
    seen: list[list[str]] = []  # noqa: RUF012 - shared test spy

    def __init__(self, model_id: str) -> None:
        type(self).loads += 1
        self.model_id = model_id

    def encode(self, texts: list[str], **options: Any) -> list[list[float]]:
        type(self).seen.append(list(texts))
        if any("explode" in text for text in texts):
            raise RuntimeError("model crashed")
        return [[float(len(text)), 1.0] for text in texts]


@pytest.fixture
def stub_sdk(monkeypatch: pytest.MonkeyPatch) -> type[_StubModel]:
    _StubModel.loads = 0
    _StubModel.seen = []
    module = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = _StubModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    return _StubModel


@pytest.mark.integration
async def test_bge_models_prefix_queries_only_and_load_once(stub_sdk: type[_StubModel]) -> None:
    embedder = SentenceTransformersEmbedderAdapter("BAAI/bge-small-en-v1.5", 2)
    assert embedder.profile.fingerprint == "BAAI/bge-small-en-v1.5:2"
    assert await embedder.embed_documents([]) == []
    documents = await embedder.embed_documents(["abc"])
    query = await embedder.embed_query("abc")
    assert documents[0].values == (3.0, 1.0)
    assert query.values == (float(len(BGE_QUERY_PREFIX) + 3), 1.0)
    assert stub_sdk.loads == 1


@pytest.mark.integration
async def test_other_models_get_no_prefix_and_failures_are_wrapped(
    stub_sdk: type[_StubModel],
) -> None:
    embedder = SentenceTransformersEmbedderAdapter("some/model", 2)
    assert (await embedder.embed_query("abc")).values == (3.0, 1.0)
    with pytest.raises(EmbeddingModelError) as raised:
        await embedder.embed_documents(["explode"])
    assert raised.value.error_code == "RETRIEVAL_202_EMBEDDER_UNAVAILABLE"


@pytest.mark.model
async def test_real_bge_model_embeds_with_the_declared_dimension() -> None:
    embedder = SentenceTransformersEmbedderAdapter("BAAI/bge-small-en-v1.5", 384)
    cat, dog, tax = await embedder.embed_documents(
        ["A cat sits on the mat.", "A dog lies on the rug.", "Corporate tax filing deadlines."]
    )
    assert cat.dimension == 384
    assert math.isclose(sum(v * v for v in cat.values), 1.0, rel_tol=1e-3)

    def dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=True))

    assert dot(cat.values, dog.values) > dot(cat.values, tax.values)


@pytest.mark.integration
async def test_loading_sets_quiet_env_and_encodes_without_progress_bar(
    stub_sdk: type[_StubModel], monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in (
        "HF_HUB_DISABLE_PROGRESS_BARS",
        "TRANSFORMERS_VERBOSITY",
        "TOKENIZERS_PARALLELISM",
    ):
        monkeypatch.delenv(name, raising=False)
    options: dict[str, Any] = {}
    original = _StubModel.encode

    def spy(self: _StubModel, texts: list[str], **kwargs: Any) -> list[list[float]]:
        options.update(kwargs)
        return original(self, texts, **kwargs)

    monkeypatch.setattr(_StubModel, "encode", spy)
    await SentenceTransformersEmbedderAdapter("some/model", 2).embed_query("abc")
    assert options["show_progress_bar"] is False
    assert os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] == "1"
    assert os.environ["TRANSFORMERS_VERBOSITY"] == "error"
    assert os.environ["TOKENIZERS_PARALLELISM"] == "false"


@pytest.mark.model
def test_real_model_json_search_leaves_stderr_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "cats.md").write_text("# Cats\nfelines purr", encoding="utf-8")
    monkeypatch.setenv("VECTRA_SYNC_MAX_RETRIES", "0")
    assert run(["sync", "notes", str(docs), "--json"]) == 0
    capsys.readouterr()
    assert run(["search", "notes", "cat", "--json"]) == 0
    assert capsys.readouterr().err == ""
