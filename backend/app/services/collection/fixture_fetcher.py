import json
from pathlib import Path

from app.services.collection.fetcher import FetchResult


class FixtureFetcher:
    """Replay HTTP responses from a local fixture directory (no network)."""

    def __init__(self, base_dir: Path | str) -> None:
        self._base_dir = Path(base_dir)
        manifest_path = self._base_dir / "manifest.json"
        with manifest_path.open(encoding="utf-8") as f:
            self._manifest: dict[str, str] = json.load(f)

    def fetch(
        self,
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        filename = self._manifest.get(url)
        if filename is None:
            raise LookupError(
                f"No fixture for {url}; run `python -m scripts.capture_wayback` "
                "from a network that can reach web.archive.org"
            )
        body = (self._base_dir / filename).read_bytes()
        return FetchResult(
            url=url,
            status=200,
            body=body,
            etag=None,
            last_modified=None,
            not_modified=False,
        )
