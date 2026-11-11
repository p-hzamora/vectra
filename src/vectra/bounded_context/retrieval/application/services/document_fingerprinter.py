"""Builds the fingerprints a sync plan compares."""

from collections.abc import Iterable

from vectra.bounded_context.retrieval.application.dtos import (
    FileFailureDTO,
    ManifestEntryDTO,
    SourceFileDTO,
)
from vectra.bounded_context.retrieval.application.ports.chunking import IChunker
from vectra.bounded_context.retrieval.application.services.chunker_resolver import (
    ChunkerResolver,
)
from vectra.bounded_context.retrieval.domain.value_objects import (
    ContentHash,
    DocumentFingerprint,
    SourcePath,
)
from vectra.exceptions import AppException


class DocumentFingerprinter:
    """Turns scanned files and manifest entries into `DocumentFingerprint`s."""

    def __init__(self, resolver: ChunkerResolver) -> None:
        self._resolver: ChunkerResolver = resolver

    def scanned(
        self, files: Iterable[SourceFileDTO]
    ) -> tuple[list[DocumentFingerprint], dict[str, FileFailureDTO]]:
        """Fingerprints of the files a chunker handles, and a failure for each other file."""
        fingerprints: list[DocumentFingerprint] = []
        failures: dict[str, FileFailureDTO] = {}
        for file in files:
            path = SourcePath(value=file.path)
            try:
                chunker: IChunker = self._resolver.resolve(path)
            except AppException as error:
                failures[file.path] = FileFailureDTO(
                    path=file.path, code=error.error_code, message=error.message, attempts=0
                )
                continue
            fingerprints.append(
                DocumentFingerprint(
                    path=path,
                    content_hash=ContentHash(value=file.content_hash),
                    chunker_version=chunker.chunker_version,
                )
            )
        return fingerprints, failures

    def indexed(self, entries: Iterable[ManifestEntryDTO]) -> list[DocumentFingerprint]:
        """Fingerprints of what the manifest says is indexed."""
        return [
            DocumentFingerprint(
                path=SourcePath(value=entry.path),
                content_hash=ContentHash(value=entry.content_hash),
                chunker_version=entry.chunker_version,
            )
            for entry in entries
        ]
