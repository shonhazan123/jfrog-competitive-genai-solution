from urllib.parse import urlparse
import httpx
from protego import Protego
from app.settings import settings

class RobotsCache:
    """One parsed robots.txt per origin, cached for the process lifetime."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=10, follow_redirects=True)
        self._parsers: dict[str, Protego] = {}

    def _parser_for(self, origin: str) -> Protego:
        if origin not in self._parsers:
            try:
                response = self._client.get(f"{origin}/robots.txt")
                text = response.text if response.status_code == 200 else ""
            except httpx.HTTPError:
                text = ""
            self._parsers[origin] = Protego.parse(text)
        return self._parsers[origin]

    def allowed(self, url: str) -> bool:
        parts = urlparse(url)
        return self._parser_for(f"{parts.scheme}://{parts.netloc}").can_fetch(
            url, settings.user_agent
        )

    def crawl_delay(self, url: str) -> float | None:
        parts = urlparse(url)
        return self._parser_for(f"{parts.scheme}://{parts.netloc}").crawl_delay(
            settings.user_agent
        )
