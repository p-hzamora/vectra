"""The latest GitHub release of vectra, read with the standard library."""

import http.client
import json
from urllib import error, request

from vectra.bounded_context.updates.application.dtos import ReleaseInfoDTO
from vectra.bounded_context.updates.application.ports.release_source import IReleaseSource
from vectra.exceptions import ReleaseSourceUnavailableError

LATEST_RELEASE_URL: str = "https://api.github.com/repos/p-hzamora/vectra/releases/latest"
TIMEOUT_SECONDS: float = 10.0
_MAX_BYTES: int = 1_000_000
_NEXT_STEPS: tuple[str, ...] = (
    "Check your network and retry `vectra update --check`.",
    "GitHub rate-limits anonymous requests; wait a few minutes if you ran this repeatedly.",
)


class GithubReleaseSourceAdapter(IReleaseSource):
    """One unauthenticated GET of the `releases/latest` endpoint.

    Args:
        user_agent: Value of the `User-Agent` header (GitHub requires one).
        url: Endpoint; only `http(s)` is allowed. Overridden by tests to a local server.
        timeout: Seconds to wait for the connection and each read.
        opener: Replacement URL opener (tests); defaults to the standard one.
    """

    def __init__(
        self,
        *,
        user_agent: str,
        url: str = LATEST_RELEASE_URL,
        timeout: float = TIMEOUT_SECONDS,
        opener: request.OpenerDirector | None = None,
    ) -> None:
        self._user_agent: str = user_agent
        self._url: str = url
        self._timeout: float = timeout
        self._opener: request.OpenerDirector = opener or request.build_opener()

    def latest_release(self) -> ReleaseInfoDTO | None:
        if not self._url.startswith(("https://", "http://")):
            raise self._unavailable(f"Refusing to read a non-HTTP URL: {self._url}")
        call = request.Request(  # noqa: S310 - scheme checked above
            self._url,
            headers={"User-Agent": self._user_agent, "Accept": "application/vnd.github+json"},
        )
        try:
            with self._opener.open(call, timeout=self._timeout) as response:
                payload: bytes = response.read(_MAX_BYTES)
        except error.HTTPError as failure:
            failure.close()
            if failure.code == 404:
                return None
            raise self._unavailable(f"GitHub answered HTTP {failure.code}.") from failure
        except (error.URLError, http.client.HTTPException, OSError) as failure:
            raise self._unavailable(f"Could not reach GitHub: {failure}") from failure
        return self._parse(payload)

    def _parse(self, payload: bytes) -> ReleaseInfoDTO:
        try:
            body: object = json.loads(payload)
        except ValueError as failure:
            raise self._unavailable("GitHub answered with something that is not JSON.") from failure
        if not isinstance(body, dict):
            raise self._unavailable("GitHub answered with an unexpected JSON document.")
        tag_name: object = body.get("tag_name")
        prerelease: object = body.get("prerelease", False)
        draft: object = body.get("draft", False)
        if (
            not isinstance(tag_name, str)
            or not isinstance(prerelease, bool)
            or not isinstance(draft, bool)
        ):
            raise self._unavailable("GitHub's release has no usable tag_name, prerelease or draft.")
        return ReleaseInfoDTO(tag_name=tag_name, prerelease=prerelease, draft=draft)

    def _unavailable(self, message: str) -> ReleaseSourceUnavailableError:
        return ReleaseSourceUnavailableError(
            message, {"url": self._url}, next_steps=list(_NEXT_STEPS)
        )
