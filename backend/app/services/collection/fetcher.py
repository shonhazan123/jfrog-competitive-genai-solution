from dataclasses import dataclass
from typing import Protocol
import httpx
from app.services.collection.ratelimit import DomainRateLimiter
from app.settings import settings

@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    body: bytes | None
    etag: str | None
    last_modified: str | None
    not_modified: bool

class Fetcher(Protocol):
    def fetch(self, url: str, etag: str | None = None,
              last_modified: str | None = None) -> FetchResult: ...

class StaticFetcher:
    def __init__(self, client: httpx.Client | None = None,
                 limiter: DomainRateLimiter | None = None) -> None:
        self._client = client or httpx.Client(timeout=20, follow_redirects=True)
        self._limiter = limiter or DomainRateLimiter()

    def fetch(self, url: str, etag: str | None = None,
              last_modified: str | None = None) -> FetchResult:
        self._limiter.acquire(url)
        headers = {"User-Agent": settings.user_agent}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        response = self._client.get(url, headers=headers)
        not_modified = response.status_code == 304
        return FetchResult(
            url=url,
            status=response.status_code,
            body=None if not_modified else response.content,
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
            not_modified=not_modified,
        )

class BrowserFetcher:
    """Adapter seam for JavaScript-rendered sources. Not built — see ARCHITECTURE.md §2."""

    def fetch(self, url: str, etag: str | None = None,
              last_modified: str | None = None) -> FetchResult:
        raise NotImplementedError(
            f"{url} requires browser rendering; no BrowserFetcher is configured. "
            "Mark the source requires_js=false or add a Playwright service."
        )
