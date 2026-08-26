import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote
from app.services.collection.fetcher import Fetcher

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
RAW_PREFIX = "https://web.archive.org/web"

@dataclass(frozen=True)
class Snapshot:
    timestamp: datetime
    digest: str
    original_url: str

    @property
    def raw_url(self) -> str:
        stamp = self.timestamp.strftime("%Y%m%d%H%M%S")
        return f"{RAW_PREFIX}/{stamp}id_/{self.original_url}"

def list_snapshots(url: str, fetcher: Fetcher, limit: int = 60) -> list[Snapshot]:
    """List archived versions where the content actually changed.

    collapse=digest asks the archive to omit consecutive identical captures, so
    every returned row is a real content change rather than a re-crawl.
    """
    query = (f"{CDX_ENDPOINT}?url={quote(url, safe='')}"
             f"&output=json&limit={limit}&collapse=digest&filter=statuscode:200")
    result = fetcher.fetch(query)
    if not result.body:
        return []

    rows = json.loads(result.body)
    snapshots = [
        Snapshot(
            timestamp=datetime.strptime(row[1], "%Y%m%d%H%M%S").replace(tzinfo=UTC),
            digest=row[5],
            original_url=row[2],
        )
        for row in rows[1:]
    ]
    return sorted(snapshots, key=lambda s: s.timestamp)
