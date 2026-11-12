"""A release as the release source reports it."""

from vectra.utils import FrozenObject


class ReleaseInfoDTO(FrozenObject):
    """The latest release.

    Attributes:
        tag_name: Git tag of the release, unchecked.
        prerelease: Marked as a pre-release.
        draft: Marked as a draft.
    """

    tag_name: str
    prerelease: bool = False
    draft: bool = False
