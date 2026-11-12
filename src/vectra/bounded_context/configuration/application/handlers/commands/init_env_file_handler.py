"""Create the env file with every setting commented out at its default."""

from pathlib import Path

from vectra.bounded_context.configuration.application.dtos import EnvFileInitResultDTO
from vectra.bounded_context.configuration.application.ports.env_file import IEnvFileWriter
from vectra.bounded_context.configuration.domain import ENV_FILE_TEMPLATE
from vectra.exceptions import EnvFileExistsError
from vectra.shared_kernel.application.handlers import IHandler
from vectra.utils import FrozenObject


class InitEnvFileCommand(FrozenObject):
    """Write the env file template.

    Attributes:
        env_file: Where to write it.
        force: Replace a file that already exists.
    """

    env_file: Path
    force: bool = False


class InitEnvFileHandler(IHandler[InitEnvFileCommand, EnvFileInitResultDTO]):
    """Writes the template unless a file is there and `force` is off."""

    def __init__(self, *, writer: IEnvFileWriter) -> None:
        self._writer: IEnvFileWriter = writer

    async def handle(self, action: InitEnvFileCommand) -> EnvFileInitResultDTO:
        """Write the template.

        Raises:
            EnvFileExistsError: A file exists and `force` is off.
        """
        existed: bool = self._writer.exists(action.env_file)
        if existed and not action.force:
            raise EnvFileExistsError(
                f"{action.env_file} already exists.",
                {"env_file": str(action.env_file)},
                next_steps=["Edit it, or run `vectra config init --force` to overwrite it."],
            )
        self._writer.write(action.env_file, ENV_FILE_TEMPLATE)
        return EnvFileInitResultDTO(env_file=str(action.env_file), overwritten=existed)
