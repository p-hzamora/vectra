"""Collapses chunk hits into one hit per document."""

from collections.abc import Sequence

from vectra.bounded_context.retrieval.application.dtos import ChunkHitDTO, DocumentHitDTO

OVER_FETCH_FACTOR: int = 4
SNIPPET_CHARS: int = 300


class DocumentHitGrouper:
    """Keeps the best chunk of each document and cuts its text into a snippet."""

    def group(self, hits: Sequence[ChunkHitDTO], top_k: int) -> tuple[DocumentHitDTO, ...]:
        """The `top_k` best documents, best score first (ties by path)."""
        best: dict[str, ChunkHitDTO] = {}
        for hit in hits:
            current: ChunkHitDTO | None = best.get(hit.path)
            if current is None or hit.score > current.score:
                best[hit.path] = hit
        ranked: list[ChunkHitDTO] = sorted(best.values(), key=lambda hit: (-hit.score, hit.path))
        return tuple(
            DocumentHitDTO(
                path=hit.path,
                score=hit.score,
                heading_path=hit.heading_path,
                snippet=_snippet(hit.text),
                chunk_id=hit.chunk_id,
            )
            for hit in ranked[:top_k]
        )


def _snippet(text: str) -> str:
    return text if len(text) <= SNIPPET_CHARS else text[:SNIPPET_CHARS].rstrip() + "..."
