"""The GitHub adapter against a local HTTP server: no request leaves the machine."""

import json
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from vectra.bounded_context.updates.infrastructure.outbound.release_source import (
    GithubReleaseSourceAdapter,
)
from vectra.exceptions import ReleaseSourceUnavailableError

pytestmark = pytest.mark.integration


class Scripted(BaseHTTPRequestHandler):
    status: int = 200
    body: bytes = b"{}"
    delay: float = 0.0
    seen_user_agents: list[str] = []  # noqa: RUF012 - shared with the test on purpose

    def do_GET(self) -> None:
        type(self).seen_user_agents.append(self.headers.get("User-Agent", ""))
        time.sleep(type(self).delay)
        try:
            self.send_response(type(self).status)
            self.send_header("Content-Length", str(len(type(self).body)))
            self.end_headers()
            self.wfile.write(type(self).body)
        except OSError:  # the client gave up (timeout test)
            pass

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def server() -> Iterator[tuple[type[Scripted], str]]:
    class Handler(Scripted):
        seen_user_agents = []  # noqa: RUF012

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield Handler, f"http://127.0.0.1:{httpd.server_port}/releases/latest"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def adapter(url: str, timeout: float = 5.0) -> GithubReleaseSourceAdapter:
    return GithubReleaseSourceAdapter(user_agent="vectra/9.9.9", url=url, timeout=timeout)


def test_reads_the_latest_release(server: tuple[type[Scripted], str]) -> None:
    handler, url = server
    handler.body = json.dumps({"tag_name": "v1.2.3", "prerelease": False, "draft": False}).encode()
    release = adapter(url).latest_release()
    assert release is not None
    assert (release.tag_name, release.prerelease, release.draft) == ("v1.2.3", False, False)
    assert handler.seen_user_agents == ["vectra/9.9.9"]


def test_missing_flags_default_to_false(server: tuple[type[Scripted], str]) -> None:
    handler, url = server
    handler.body = b'{"tag_name": "v1.2.3"}'
    release = adapter(url).latest_release()
    assert release is not None
    assert (release.prerelease, release.draft) == (False, False)


def test_404_means_no_release(server: tuple[type[Scripted], str]) -> None:
    handler, url = server
    handler.status = 404
    assert adapter(url).latest_release() is None


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
def test_failures_are_unavailable(
    server: tuple[type[Scripted], str], status: int, body: bytes
) -> None:
    handler, url = server
    handler.status, handler.body = status, body
    with pytest.raises(ReleaseSourceUnavailableError) as raised:
        adapter(url).latest_release()
    assert raised.value.error_code == "UPDATES_201_RELEASE_SOURCE_UNAVAILABLE"
    assert raised.value.next_steps


def test_a_slow_server_times_out(server: tuple[type[Scripted], str]) -> None:
    handler, url = server
    handler.delay = 1.0
    with pytest.raises(ReleaseSourceUnavailableError):
        adapter(url, timeout=0.2).latest_release()


def test_an_unreachable_host_is_unavailable() -> None:
    with pytest.raises(ReleaseSourceUnavailableError):
        adapter("http://127.0.0.1:1/releases/latest", timeout=1.0).latest_release()


def test_only_http_schemes_are_requested() -> None:
    with pytest.raises(ReleaseSourceUnavailableError):
        adapter("file:///etc/passwd").latest_release()
