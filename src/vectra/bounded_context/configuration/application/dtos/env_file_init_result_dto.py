"""Outcome of creating an env file."""

from vectra.utils import FrozenObject


class EnvFileInitResultDTO(FrozenObject):
    """An env file was written.

    Attributes:
        env_file: The file written.
        overwritten: Whether a file was already there and was replaced.
    """

    env_file: str
    overwritten: bool
