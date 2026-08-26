import json
from datetime import UTC
from urllib.parse import quote

from app.models.capture import RawCapture
from app.models.ledger import ClaimVersion
from app.services.backfill import backfill_source
from app.services.collection.fetcher import FetchResult
from app.services.collection.fixture_fetcher import FixtureFetcher
from app.services.collection.wayback import CDX_ENDPOINT, list_snapshots
from scripts.capture_wayback import RecordingFetcher

V1 = b"<html><body><table><tr><th>Capability</th><th>JFrog</th></tr>" \
     b"<tr><td>Malware detection</td><td>Limited</td></tr></table></body></html>"
V2 = b"<html><body><table><tr><th>Capability</th><th>JFrog</th></tr>" \
     b"<tr><td>Malware detection</td><td>Very limited, not proactive</td></tr></table></body></html>"


class MappingFetcher:
    def __init__(self, pages: dict[str, bytes]) -> None:
        self.pages = pages

    def fetch(self, url: str, etag: str | None = None, last_modified: str | None = None) -> FetchResult:
        return FetchResult(url, 200, self.pages[url], None, None, False)


def _cdx_query(url: str) -> str:
    return (
        f"{CDX_ENDPOINT}?url={quote(url, safe='')}"
        f"&output=json&limit=60&collapse=digest&filter=statuscode:200"
    )


def test_capture_and_replay_round_trip(session, seeded_source, tmp_path) -> None:
    source_url = seeded_source.url
    cdx_body = json.dumps([
        ["urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length"],
        ["com,sonatype)/compare", "20210227194637", source_url,
         "text/html", "200", "DIGEST1", "100"],
        ["com,sonatype)/compare", "20260510141655", source_url,
         "text/html", "200", "DIGEST2", "200"],
    ]).encode()
    cdx_query = _cdx_query(source_url)
    raw_v1 = (
        "https://web.archive.org/web/20210227194637id_/" + source_url
    )
    raw_v2 = (
        "https://web.archive.org/web/20260510141655id_/" + source_url
    )
    inner = MappingFetcher({
        cdx_query: cdx_body,
        raw_v1: V1,
        raw_v2: V2,
    })

    recording = RecordingFetcher(inner, tmp_path)
    snapshots = list_snapshots(source_url, recording)
    for snapshot in snapshots:
        recording.fetch(snapshot.raw_url)
    recording.write_manifest()

    report = backfill_source(session, seeded_source, FixtureFetcher(tmp_path))

    assert report.captures == 2
    assert session.query(RawCapture).filter_by(provenance="archive").count() == 2

    version = session.query(ClaimVersion).one()
    assert version.old_text == "Limited"
    assert version.new_text == "Very limited, not proactive"
    assert version.change_kind == "substantive"
