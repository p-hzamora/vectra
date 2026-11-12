"""Init env file handler."""

from pathlib import Path

import pytest

from vectra.bounded_context.configuration.application.handlers.commands import (
    InitEnvFileCommand,
    InitEnvFileHandler,
)
from vectra.bounded_context.configuration.application.ports.env_file import IEnvFileWriter
from vectra.bounded_context.configuration.domain import ENV_FILE_TEMPLATE
from vectra.exceptions import EnvFileExistsError

pytestmark = pytest.mark.unit


class FakeEnvFileWriter(IEnvFileWriter):
    def __init__(self, files: dict[Path, str] | None = None) -> None:
        self.files: dict[Path, str] = files or {}

    def exists(self, path: Path) -> bool:
        return path in self.files

    def write(self, path: Path, content: str) -> None:
        self.files[path] = content


TARGET: Path = Path("/cfg/vectra/.env")


async def test_writes_the_template_when_nothing_is_there() -> None:
    writer = FakeEnvFileWriter()
    result = await InitEnvFileHandler(writer=writer).handle(InitEnvFileCommand(env_file=TARGET))
    assert writer.files == {TARGET: ENV_FILE_TEMPLATE}
    assert (result.env_file, result.overwritten) == (str(TARGET), False)


async def test_refuses_to_replace_a_file_without_force() -> None:
    writer = FakeEnvFileWriter({TARGET: "mine"})
    with pytest.raises(EnvFileExistsError) as raised:
        await InitEnvFileHandler(writer=writer).handle(InitEnvFileCommand(env_file=TARGET))
    assert raised.value.error_code == "CONFIGURATION_101_ENV_FILE_EXISTS"
    assert writer.files == {TARGET: "mine"}


async def test_force_replaces_the_file() -> None:
    writer = FakeEnvFileWriter({TARGET: "mine"})
    result = await InitEnvFileHandler(writer=writer).handle(
        InitEnvFileCommand(env_file=TARGET, force=True)
    )
    assert writer.files == {TARGET: ENV_FILE_TEMPLATE}
    assert result.overwritten is True
