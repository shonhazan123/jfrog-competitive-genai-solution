import json
from datetime import UTC, datetime
from types import SimpleNamespace

from app.models.capture import RawCapture
from app.models.ledger import ClaimVersion
from app.services.snapshot import collect_snapshot_source
from app.services.collection.apis.greenhouse import GreenhouseAdapter
from app.services.collection.apis.hackernews import HackerNewsAdapter
from app.services.collection.apis.lever import LeverAdapter
from app.services.collection.fetcher import FetchResult

V1 = b"<html><body><table><tr><th>Capability</th><th>JFrog</th></tr>" \
     b"<tr><td>Malware detection</td><td>Limited</td></tr></table></body></html>"
V2 = b"<html><body><table><tr><th>Capability</th><th>JFrog</th></tr>" \
     b"<tr><td>Malware detection</td><td>Very limited, not proactive</td></tr></table></body></html>"


class ScriptedFetcher:
    def __init__(self, pages):
        self.pages = pages

    def fetch(self, url, etag=None, last_modified=None):
        return FetchResult(url, 200, self.pages[url], None, None, False)


def _static(body: bytes):
    class _F:
        def fetch(self, url, etag=None, last_modified=None):
            return FetchResult(url, 200, body, None, None, False)
    return _F()


# --- live snapshot collection -------------------------------------------------------------

def test_live_snapshot_records_a_claim_version_on_change(session, seeded_source):
    """A change to a tracked page between two live collections records a ClaimVersion
    against the same claim, with provenance 'live'."""
    # First collection establishes the baseline version.
    baseline = collect_snapshot_source(session, seeded_source, ScriptedFetcher({seeded_source.url: V1}))
    assert baseline == 1

    # A later collection sees the changed page and records the version delta.
    created = collect_snapshot_source(session, seeded_source, ScriptedFetcher({seeded_source.url: V2}))

    assert created == 1
    assert session.query(RawCapture).filter_by(provenance="live").count() == 2
    version = session.query(ClaimVersion).one()
    assert version.old_text == "Limited"
    assert version.new_text == "Very limited, not proactive"


def test_live_snapshot_skips_when_page_is_unchanged(session, seeded_source):
    # First collection establishes the baseline.
    collect_snapshot_source(session, seeded_source, ScriptedFetcher({seeded_source.url: V1}))

    # Same content as the last stored version -> no new capture, no version.
    created = collect_snapshot_source(session, seeded_source, ScriptedFetcher({seeded_source.url: V1}))

    assert created == 0
    assert session.query(RawCapture).filter_by(provenance="live").count() == 1


# --- adapters -----------------------------------------------------------------------------

def test_greenhouse_adapter_maps_jobs_to_talent_org():
    body = json.dumps({"jobs": [{
        "id": 4213, "title": "Staff Malware Research Engineer", "content": "Build detections.",
        "updated_at": "2026-08-01T12:00:00Z", "absolute_url": "https://jobs.example/4213",
        "location": {"name": "Remote - US"},
    }]}).encode()

    records = GreenhouseAdapter().collect(SimpleNamespace(url="https://boards.example"), _static(body))

    assert len(records) == 1
    assert records[0].external_id == "4213"
    assert records[0].signal_type_hint == "talent_org"
    assert records[0].extra["location"] == "Remote - US"
    assert records[0].occurred_at == datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def test_lever_adapter_maps_postings_to_talent_org():
    body = json.dumps([{
        "id": "099a2300-3d4d-4dab-9f5c-eaba27c64be5", "text": "Staff Malware Research Engineer",
        "createdAt": 1781858910353, "descriptionPlain": "Build detections.",
        "hostedUrl": "https://jobs.lever.co/sonatype/099a2300",
        "categories": {"team": "Research", "location": "Remote", "commitment": "Full-Time"},
    }]).encode()

    records = LeverAdapter().collect(SimpleNamespace(url="https://api.lever.co/..."), _static(body))

    assert len(records) == 1
    assert records[0].external_id == "099a2300-3d4d-4dab-9f5c-eaba27c64be5"
    assert records[0].signal_type_hint == "talent_org"
    assert records[0].extra["team"] == "Research"
    assert records[0].url == "https://jobs.lever.co/sonatype/099a2300"
    assert records[0].occurred_at is not None and records[0].occurred_at.tzinfo is not None


def test_hackernews_adapter_maps_hits_and_falls_back_to_item_url():
    body = json.dumps({"hits": [
        {"objectID": "111", "title": "Artifactory is slow at scale", "url": "https://blog/x",
         "created_at": "2026-08-10T00:00:00Z", "points": 42, "num_comments": 30},
        {"objectID": "222", "comment_text": "we hit the same rate limits", "url": None,
         "created_at": "2026-08-11T00:00:00Z"},
    ]}).encode()

    records = HackerNewsAdapter().collect(SimpleNamespace(url="https://hn.example"), _static(body))

    assert [r.external_id for r in records] == ["111", "222"]
    assert records[0].extra["points"] == 42
    assert records[1].url == "https://news.ycombinator.com/item?id=222"
    assert records[1].body == "we hit the same rate limits"


def test_adapters_are_registered_in_the_collection_job():
    from worker.jobs import _ADAPTERS
    assert set(_ADAPTERS) >= {"osv", "greenhouse", "lever", "hn"}
