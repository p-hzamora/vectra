"""Env files on the local filesystem."""

from pathlib import Path

from vectra.bounded_context.configuration.application.ports.env_file import IEnvFileWriter


class FilesystemEnvFileWriterAdapter(IEnvFileWriter):
    """Reads and writes env files with `pathlib`."""

    def exists(self, path: Path) -> bool:
        return path.exists()

    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
