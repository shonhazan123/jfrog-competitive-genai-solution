import json
from app.services.collection.fetcher import FetchResult
from app.services.collection.apis.osv import OsvAdapter

PAYLOAD = json.dumps({"vulns": [{
    "id": "GHSA-xxxx-yyyy-zzzz",
    "summary": "Authentication bypass in Nexus Repository",
    "details": "A flaw allows unauthenticated access to repository contents.",
    "published": "2026-08-14T10:00:00Z",
    "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}],
    "references": [{"type": "ADVISORY", "url": "https://osv.dev/GHSA-xxxx-yyyy-zzzz"}],
}]}).encode()

class FakeFetcher:
    def __init__(self, body): self.body = body
    def fetch(self, url, etag=None, last_modified=None):
        return FetchResult(url, 200, self.body, None, None, False)

def test_maps_osv_records_to_api_records(seeded_api_source):
    records = OsvAdapter().collect(seeded_api_source, FakeFetcher(PAYLOAD))
    assert len(records) == 1
    assert records[0].external_id == "GHSA-xxxx-yyyy-zzzz"
    assert records[0].signal_type_hint == "security_trust"
    assert records[0].occurred_at.year == 2026

def test_extracts_cvss_score_for_the_interrupt_rule(seeded_api_source):
    record = OsvAdapter().collect(seeded_api_source, FakeFetcher(PAYLOAD))[0]
    assert record.extra["cvss"] >= 9.0

def test_empty_result_is_not_an_error(seeded_api_source):
    assert OsvAdapter().collect(seeded_api_source, FakeFetcher(b'{"vulns": []}')) == []
