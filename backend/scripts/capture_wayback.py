"""Capture Internet Archive responses into offline fixtures for replay."""

import hashlib
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.registry import Source
from app.services.collection.fetcher import Fetcher, FetchResult, StaticFetcher
from app.services.collection.wayback import list_snapshots
from app.settings import settings


class RecordingFetcher:
    """Wraps a fetcher and records every response body into a fixture directory."""

    def __init__(self, inner: Fetcher, out_dir: Path | str) -> None:
        self._inner = inner
        self._out_dir = Path(out_dir)
        self._out_dir.mkdir(parents=True, exist_ok=True)
        self._manifest: dict[str, str] = {}

    def fetch(
        self,
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        result = self._inner.fetch(url, etag=etag, last_modified=last_modified)
        if result.body is not None:
            filename = f"{hashlib.sha256(url.encode()).hexdigest()[:16]}.bin"
            (self._out_dir / filename).write_bytes(result.body)
            self._manifest[url] = filename
        return result

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
