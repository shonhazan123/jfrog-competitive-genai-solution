from datetime import UTC, datetime
from app.services.collection.fetcher import FetchResult
from app.services.collection.wayback import Snapshot
from app.services.backfill import backfill_source
from app.models.ledger import Claim, ClaimVersion
from app.models.capture import RawCapture

V1 = b"<html><body><table><tr><th>Capability</th><th>JFrog</th></tr>" \
     b"<tr><td>Malware detection</td><td>Limited</td></tr></table></body></html>"
V2 = b"<html><body><table><tr><th>Capability</th><th>JFrog</th></tr>" \
     b"<tr><td>Malware detection</td><td>Very limited, not proactive</td></tr></table></body></html>"

class ScriptedFetcher:
    def __init__(self, pages): self.pages = pages
    def fetch(self, url, etag=None, last_modified=None):
        return FetchResult(url, 200, self.pages[url], None, None, False)

def test_backfill_creates_one_capture_per_snapshot(session, seeded_source, monkeypatch):
    snapshots = [
        Snapshot(datetime(2021, 2, 27, tzinfo=UTC), "d1", "https://x.test/c"),
        Snapshot(datetime(2026, 5, 10, tzinfo=UTC), "d2", "https://x.test/c"),
    ]
    monkeypatch.setattr("app.services.backfill.list_snapshots", lambda *a, **k: snapshots)
    fetcher = ScriptedFetcher({snapshots[0].raw_url: V1, snapshots[1].raw_url: V2})

    report = backfill_source(session, seeded_source, fetcher)

    assert report.captures == 2
    assert session.query(RawCapture).filter_by(provenance="archive").count() == 2

def test_backfill_records_the_claim_change_between_versions(session, seeded_source, monkeypatch):
    snapshots = [
        Snapshot(datetime(2021, 2, 27, tzinfo=UTC), "d1", "https://x.test/c"),
        Snapshot(datetime(2026, 5, 10, tzinfo=UTC), "d2", "https://x.test/c"),
    ]
    monkeypatch.setattr("app.services.backfill.list_snapshots", lambda *a, **k: snapshots)
    fetcher = ScriptedFetcher({snapshots[0].raw_url: V1, snapshots[1].raw_url: V2})

    backfill_source(session, seeded_source, fetcher)

    version = session.query(ClaimVersion).one()
    assert version.old_text == "Limited"
    assert version.new_text == "Very limited, not proactive"
    assert version.change_kind == "substantive"

def test_claim_subject_is_jfrog_and_asserter_is_the_source_entity(session, seeded_source, monkeypatch):
    snapshots = [Snapshot(datetime(2021, 2, 27, tzinfo=UTC), "d1", "https://x.test/c")]
    monkeypatch.setattr("app.services.backfill.list_snapshots", lambda *a, **k: snapshots)
    backfill_source(session, seeded_source, ScriptedFetcher({snapshots[0].raw_url: V1}))

    from app.models.registry import Entity
    claim = session.query(Claim).one()
    assert session.get(Entity, claim.subject_entity_id).slug == "jfrog"
    assert session.get(Entity, claim.asserting_entity_id).slug == "sonatype"
