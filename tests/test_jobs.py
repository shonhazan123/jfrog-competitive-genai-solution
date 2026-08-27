from pathlib import Path
import pytest
from app.services.collection.fetcher import FetchResult
from app.services.collection.robots import RobotsCache

ATOM = (Path(__file__).parent / "fixtures" / "nexus_releases.atom").read_bytes()

@pytest.fixture(autouse=True)
def _allow_robots_for_jobs(monkeypatch):
    monkeypatch.setattr(RobotsCache, "allowed", lambda self, url: True)

class DenyRobots:
    def allowed(self, url: str) -> bool:
        return False

@pytest.fixture
def fake_robots_denying():
    return DenyRobots()

class ScriptedFeedFetcher:
    def fetch(self, url, etag=None, last_modified=None):
        if url.endswith(".atom") or "releases.atom" in url:
            return FetchResult(url, 200, ATOM, None, None, False)
        return FetchResult(url, 200, b'{"vulns": []}', None, None, False)

@pytest.fixture
def scripted_feed_fetcher():
    return ScriptedFeedFetcher()

def test_collection_skips_sources_disallowed_by_robots(session, monkeypatch, fake_robots_denying, scripted_feed_fetcher):
    from app.services.seeding import seed
    from worker.jobs import run_collection
    seed(session)
    report = run_collection(session=session, robots=fake_robots_denying, fetcher=scripted_feed_fetcher)
    assert report["skipped_robots"] > 0
    assert report["captures"] == 0

def test_feed_entries_already_seen_are_not_recaptured(session, scripted_feed_fetcher):
    from app.services.seeding import seed
    from worker.jobs import run_collection
    seed(session)
    first = run_collection(session=session, fetcher=scripted_feed_fetcher)
    second = run_collection(session=session, fetcher=scripted_feed_fetcher)
    assert first["captures"] > 0
    assert second["captures"] == 0


def test_manual_collection_ignores_the_due_schedule(session, scripted_feed_fetcher):
    from datetime import UTC, datetime

    from app.models.registry import Source
    from app.services.seeding import seed
    from worker.jobs import run_collection

    seed(session)
    now = datetime.now(UTC)
    for source in session.query(Source).all():
        source.last_checked_at = now
    session.flush()

    skipped = run_collection(session=session, fetcher=scripted_feed_fetcher)
    forced = run_collection(session=session, fetcher=scripted_feed_fetcher, force=True)

    assert skipped["skipped_not_due"] == skipped["sources"]
    assert forced["skipped_not_due"] == 0

def test_manual_trigger_calls_the_same_function_the_scheduler_calls():
    """The button is a convenience, not a parallel implementation."""
    import inspect
    from app.controllers.runs import trigger_collection
    assert "run_collection" in inspect.getsource(trigger_collection)


def test_run_interpret_continues_after_a_capture_failure(session, seeded_source, monkeypatch):
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from app.models.capture import RawCapture
    from worker import jobs

    captures = []
    for idx in range(2):
        capture = RawCapture(
            source_id=seeded_source.id,
            fetched_at=datetime.now(UTC),
            http_status=200,
            content_hash=f"hash-{idx}",
            blob_path=f"/tmp/{idx}",
            extracted_text=f"sample text {idx}",
            provenance="test",
        )
        session.add(capture)
        session.flush()
        captures.append(capture)
    first_id, second_id = captures[0].id, captures[1].id
    calls: list[int] = []

    def fake_interpret(capture_id, *, session):
        calls.append(capture_id)
        if capture_id == first_id:
            raise TimeoutError("Request timed out.")
        return SimpleNamespace(status="ok", signal_id=99, thread_id=f"interpret:{capture_id}:v1")

    monkeypatch.setattr(jobs, "interpret_capture", fake_interpret)

    report = jobs.run_interpret(session=session, limit=2)

    assert calls == [first_id, second_id]
    assert report["failed"] == 1
    assert report["interpreted"] == 1
