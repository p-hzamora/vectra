"""The GitHub adapter against a scripted opener: no request leaves the machine."""

import io
import json
from email.message import Message
from urllib import error, request

import pytest

from vectra.bounded_context.updates.infrastructure.outbound.release_source import (
    GithubReleaseSourceAdapter,
)
from vectra.bounded_context.updates.infrastructure.outbound.release_source.github_release_source_adapter import (
    LATEST_RELEASE_URL,
    TIMEOUT_SECONDS,
)
from vectra.exceptions import ReleaseSourceUnavailableError

pytestmark = pytest.mark.integration

URL: str = "https://example.test/releases/latest"


class ScriptedOpener(request.OpenerDirector):
    """Answers every request with the scripted status and body, or raises the scripted failure."""

    def __init__(self, *, status: int = 200, body: bytes = b"{}", raises: Exception | None = None):
        super().__init__()
        self.status: int = status
        self.body: bytes = body
        self.raises: Exception | None = raises
        self.calls: list[request.Request] = []
        self.timeouts: list[float | None] = []

    def open(  # type: ignore[override]
        self, fullurl: request.Request, data: None = None, timeout: float | None = None
    ) -> io.BytesIO:
        self.calls.append(fullurl)
        self.timeouts.append(timeout)
        if self.raises is not None:
            raise self.raises
        if self.status >= 400:
            raise error.HTTPError(
                fullurl.full_url, self.status, "scripted", Message(), io.BytesIO(self.body)
            )
        return io.BytesIO(self.body)


def adapter(opener: ScriptedOpener, url: str = URL) -> GithubReleaseSourceAdapter:
    return GithubReleaseSourceAdapter(user_agent="vectra/9.9.9", url=url, opener=opener)


def test_reads_the_latest_release() -> None:
    opener = ScriptedOpener(
        body=json.dumps({"tag_name": "v1.2.3", "prerelease": False, "draft": False}).encode()
    )
    release = adapter(opener).latest_release()
    assert release is not None
    assert (release.tag_name, release.prerelease, release.draft) == ("v1.2.3", False, False)
    assert opener.calls[0].full_url == URL
    assert opener.calls[0].get_header("User-agent") == "vectra/9.9.9"
    assert opener.timeouts == [TIMEOUT_SECONDS]


def test_the_default_endpoint_is_https() -> None:
    opener = ScriptedOpener(body=b'{"tag_name": "v1.2.3"}')
    GithubReleaseSourceAdapter(user_agent="vectra/9.9.9", opener=opener).latest_release()
    assert LATEST_RELEASE_URL.startswith("https://")
    assert opener.calls[0].full_url == LATEST_RELEASE_URL


def test_missing_flags_default_to_false() -> None:
    release = adapter(ScriptedOpener(body=b'{"tag_name": "v1.2.3"}')).latest_release()
    assert release is not None
    assert (release.prerelease, release.draft) == (False, False)


def test_404_means_no_release() -> None:
    assert adapter(ScriptedOpener(status=404)).latest_release() is None


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (403, b'{"message": "rate limit exceeded"}'),
        (500, b""),
        (200, b"not json"),
        (200, b"[]"),
        (200, b'{"name": "no tag"}'),
        (200, b'{"tag_name": 3}'),
        (200, b'{"tag_name": "v1.0.0", "draft": "yes"}'),
    ],
)
def test_failures_are_unavailable(status: int, body: bytes) -> None:
    with pytest.raises(ReleaseSourceUnavailableError) as raised:
        adapter(ScriptedOpener(status=status, body=body)).latest_release()
    assert raised.value.error_code == "UPDATES_201_RELEASE_SOURCE_UNAVAILABLE"
    assert raised.value.next_steps


@pytest.mark.parametrize(
    "failure",
    [TimeoutError("timed out"), error.URLError("no route to host")],
)
def test_a_network_failure_is_unavailable(failure: Exception) -> None:
    with pytest.raises(ReleaseSourceUnavailableError):
        adapter(ScriptedOpener(raises=failure)).latest_release()


@pytest.mark.parametrize(
    "url", ["http://example.test/releases/latest", "file:///etc/passwd", "ftp://example.test/x"]
)
def test_only_https_is_requested(url: str) -> None:
    opener = ScriptedOpener()
    with pytest.raises(ReleaseSourceUnavailableError):
        adapter(opener, url).latest_release()
    assert opener.calls == []
