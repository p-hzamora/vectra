"""Embedding adapters: the only package that imports `sentence_transformers`."""

from .sentence_transformers_embedder_adapter import SentenceTransformersEmbedderAdapter

__all__ = ["SentenceTransformersEmbedderAdapter"]
