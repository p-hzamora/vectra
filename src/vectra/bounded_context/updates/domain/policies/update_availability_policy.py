"""Which releases count and whether one is an update."""

from vectra.bounded_context.updates.domain.value_objects import ReleaseTag, Version
from vectra.exceptions import InvalidVersionError


class UpdateAvailabilityPolicy:
    """Only published, strict `vX.Y.Z` releases count; anything else is as if absent."""

    def accepted_tag(self, *, tag_name: str, prerelease: bool, draft: bool) -> ReleaseTag | None:
        """The release tag, or `None` for a prerelease, a draft or a tag that is not `vX.Y.Z`."""
        if prerelease or draft:
            return None
        try:
            return ReleaseTag.parse(tag_name)
        except InvalidVersionError:
            return None

    def current(self, text: str) -> Version | None:
        """The installed version, or `None` for a dev or source build."""
        try:
            return Version.parse(text)
        except InvalidVersionError:
            return None

    def availability(self, *, current: Version | None, latest: ReleaseTag | None) -> bool | None:
        """Whether `latest` is newer than `current`.

        Returns:
            `False` without a release or when installed is not older; `None` when the installed
            version is not a release (cannot be compared); otherwise `True`.
        """
        if latest is None:
            return False
        if current is None:
            return None
        return latest.version.is_newer_than(current)
