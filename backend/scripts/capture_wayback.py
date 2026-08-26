"""Capture Internet Archive responses into offline fixtures for replay."""

import hashlib
import json
import time
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.registry import Source
from app.services.collection.fetcher import Fetcher, FetchResult, StaticFetcher
from app.services.collection.wayback import list_snapshots
from app.settings import settings

# The Internet Archive (especially over a VPN tunnel) drops connections
# intermittently, so a single sequential pass rarely finishes. Retry each
# request on transient transport errors and resume from any fixtures already
# on disk so repeated runs accumulate progress until the capture is complete.
_MAX_ATTEMPTS = 8
_BACKOFF_SECONDS = 2.0


class RecordingFetcher:
    """Wraps a fetcher and records every response body into a fixture directory."""

    def __init__(self, inner: Fetcher, out_dir: Path | str) -> None:
        self._inner = inner
        self._out_dir = Path(out_dir)
        self._out_dir.mkdir(parents=True, exist_ok=True)
        self._manifest: dict[str, str] = {}
        self._load_existing_manifest()

    def _load_existing_manifest(self) -> None:
        manifest_path = self._out_dir / "manifest.json"
        if manifest_path.exists():
            try:
                self._manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._manifest = {}

    @staticmethod
    def _filename_for(url: str) -> str:
        return f"{hashlib.sha256(url.encode()).hexdigest()[:16]}.bin"

    def _cached_result(self, url: str) -> FetchResult | None:
        filename = self._manifest.get(url)
        if not filename:
            return None
        path = self._out_dir / filename
        if not path.exists():
            return None
        return FetchResult(
            url=url,
            status=200,
            body=path.read_bytes(),
            etag=None,
            last_modified=None,
            not_modified=False,
        )

    def fetch(
        self,
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        cached = self._cached_result(url)
        if cached is not None:
            return cached

        result = self._fetch_with_retries(url, etag=etag, last_modified=last_modified)
        if result.body is not None:
            filename = self._filename_for(url)
            (self._out_dir / filename).write_bytes(result.body)
            self._manifest[url] = filename
            self.write_manifest()
        return result

    def _fetch_with_retries(
        self,
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return self._inner.fetch(url, etag=etag, last_modified=last_modified)
            except httpx.TransportError as exc:
                last_exc = exc
                print(f"  retry {attempt}/{_MAX_ATTEMPTS} for {url}: {exc!r}")
                time.sleep(_BACKOFF_SECONDS)
        assert last_exc is not None
        raise last_exc

    def write_manifest(self) -> None:
        manifest_path = self._out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(self._manifest, indent=2), encoding="utf-8")


def capture(session: Session, out_dir: Path | str) -> list[tuple[str, int]]:
    """Fetch archive data for every enabled snapshot-mode source and write fixtures."""
    out_path = Path(out_dir)
    summaries: list[tuple[str, int]] = []
    sources = session.query(Source).filter_by(mode="snapshot", enabled=True).all()
    for source in sources:
        recording = RecordingFetcher(StaticFetcher(), out_path)
        snapshots = list_snapshots(source.url, recording)
        for snapshot in snapshots:
            recording.fetch(snapshot.raw_url)
        recording.write_manifest()
        summaries.append((source.key, len(snapshots)))
    return summaries


def main() -> None:
    out_dir = Path(settings.fixtures_dir)
    with SessionLocal() as session:
        summaries = capture(session, out_dir)
    for key, count in summaries:
        print(f"{key}: {count} snapshots")
    print(f"fixtures written to {out_dir}")


if __name__ == "__main__":
    main()
