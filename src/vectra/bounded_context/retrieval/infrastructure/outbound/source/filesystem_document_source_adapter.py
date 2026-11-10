"""Documents read from a local folder."""

import asyncio
import hashlib
import os
from collections.abc import AsyncIterator, Sequence
from pathlib import Path, PurePosixPath

from vectra.bounded_context.retrieval.application.dtos import SourceFileDTO
from vectra.bounded_context.retrieval.application.ports.source import IDocumentSource
from vectra.bounded_context.retrieval.domain.value_objects import SourcePath
from vectra.exceptions import DocumentReadError, SourceRootInvalidError


class FilesystemDocumentSourceAdapter(IDocumentSource):
    """Walks a folder in sorted order, skipping hidden folders and symbolic links."""

    async def scan(
        self, root: str, include: Sequence[str], exclude: Sequence[str]
    ) -> AsyncIterator[SourceFileDTO]:
        folder = Path(root)
        if not folder.is_dir():
            raise SourceRootInvalidError(
                f"The source root {root!r} is not a folder.",
                {"root": root},
                next_steps=["Check the path; a sync never starts from a missing root."],
            )
        for file in await asyncio.to_thread(self._scan_blocking, folder, include, exclude):
            yield file

    async def read_text(self, root: str, path: SourcePath) -> str:
        target = Path(root) / path.value
        try:
            return await asyncio.to_thread(target.read_text, encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise DocumentReadError(
                f"Cannot read {path.value!r}: {error}", {"path": path.value, "root": root}
            ) from error

    def _scan_blocking(
        self, folder: Path, include: Sequence[str], exclude: Sequence[str]
    ) -> list[SourceFileDTO]:
        files: list[SourceFileDTO] = []
        for current, directories, names in os.walk(folder, followlinks=False):
            directories[:] = sorted(
                name
                for name in directories
                if not name.startswith(".") and not (Path(current) / name).is_symlink()
            )
            for name in sorted(names):
                full = Path(current) / name
                if full.is_symlink():
                    continue
                relative: str = full.relative_to(folder).as_posix()
                posix = PurePosixPath(relative)
                if any(posix.full_match(pattern) for pattern in include) and not any(
                    posix.full_match(pattern) for pattern in exclude
                ):
                    content: bytes = full.read_bytes()
                    files.append(
                        SourceFileDTO(
                            path=relative,
                            content_hash=hashlib.sha256(content).hexdigest(),
                            size=len(content),
                        )
                    )
        return files
