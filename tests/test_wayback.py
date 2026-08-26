import json
from datetime import UTC
import pytest
from app.services.collection.fetcher import FetchResult
from app.services.collection.wayback import Snapshot, list_snapshots

CDX = json.dumps([
    ["urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length"],
    ["com,sonatype)/compare", "20210227194637", "https://www.sonatype.com/compare",
     "text/html", "200", "O2KLUGIMT67GWKVC4JFCXMA63AD4VE6E", "20225"],
    ["com,sonatype)/compare", "20260510141655", "https://www.sonatype.com/compare",
     "text/html", "200", "BG4PXMHZX4WVWVNBC66Q6EBE4R6WIWDS", "38371"],
]).encode()

class FakeFetcher:
    def __init__(self, body): self.body, self.calls = body, []
    def fetch(self, url, etag=None, last_modified=None):
        self.calls.append(url)
        return FetchResult(url, 200, self.body, None, None, False)

def test_parses_snapshots_and_drops_the_header_row():
    snapshots = list_snapshots("https://www.sonatype.com/compare", FakeFetcher(CDX))
    assert len(snapshots) == 2
    assert snapshots[0].digest == "O2KLUGIMT67GWKVC4JFCXMA63AD4VE6E"

def test_timestamps_parse_as_utc_and_sort_ascending():
    snapshots = list_snapshots("https://www.sonatype.com/compare", FakeFetcher(CDX))
    assert snapshots[0].timestamp.tzinfo is UTC
    assert snapshots[0].timestamp < snapshots[1].timestamp

def test_requests_collapse_by_digest_so_only_real_changes_are_returned():
    fetcher = FakeFetcher(CDX)
    list_snapshots("https://www.sonatype.com/compare", fetcher)
    assert "collapse=digest" in fetcher.calls[0]

def test_raw_url_uses_the_id_suffix_to_avoid_the_archive_toolbar():
    snapshots = list_snapshots("https://www.sonatype.com/compare", FakeFetcher(CDX))
    assert snapshots[0].raw_url == (
        "https://web.archive.org/web/20210227194637id_/https://www.sonatype.com/compare"
    )

def test_empty_archive_response_returns_no_snapshots():
    assert list_snapshots("https://x.test", FakeFetcher(b"")) == []

@pytest.mark.live
def test_live_archive_has_many_versions_of_the_sonatype_comparison_page():
    from app.services.collection.fetcher import StaticFetcher
    snapshots = list_snapshots(
        "https://www.sonatype.com/compare/sonatype-nexus-versus-jfrog-artifactory",
        StaticFetcher(),
    )
    assert len(snapshots) >= 10
