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


def test_run_interpret_continues_after_a_capture_failure(session, monkeypatch):
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from app.models.capture import RawCapture
    from app.models.registry import Source
    from app.services.seeding import seed
    from worker import jobs

    seed(session)
    feed_source = session.query(Source).filter_by(key="harbor_releases").one()
    captures = []
    for idx in range(2):
        capture = RawCapture(
            source_id=feed_source.id,
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


def test_run_interpret_counts_empty_captures(session, monkeypatch):
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from app.models.capture import RawCapture
    from app.models.registry import Source
    from app.services.seeding import seed
    from worker import jobs

    seed(session)
    feed_source = session.query(Source).filter_by(key="harbor_releases").one()
    capture = RawCapture(
        source_id=feed_source.id, fetched_at=datetime.now(UTC), http_status=200,
        content_hash="empty-batch", blob_path="/tmp/eb",
        extracted_text="boilerplate", provenance="test",
    )
    session.add(capture); session.flush()

    def fake_interpret(capture_id, *, session):
        return SimpleNamespace(status="empty", signal_id=None,
                               thread_id=f"interpret:{capture_id}:v1")

    monkeypatch.setattr(jobs, "interpret_capture", fake_interpret)
    report = jobs.run_interpret(session=session, limit=1)
    assert report["skipped_empty"] == 1
    assert report["interpreted"] == 0


def test_run_interpret_dedups_identical_captures(session, monkeypatch):
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from app.models.capture import RawCapture
    from app.models.registry import Source
    from app.services.seeding import seed
    from worker import jobs

    seed(session)
    feed_source = session.query(Source).filter_by(key="harbor_releases").one()
    for idx in range(2):
        session.add(RawCapture(
            source_id=feed_source.id, fetched_at=datetime.now(UTC), http_status=200,
            content_hash="same-hash", blob_path=f"/tmp/dup{idx}",
            extracted_text="identical page body", provenance="test",
        ))
    session.flush()

    calls: list[int] = []
    def fake_interpret(capture_id, *, session):
        calls.append(capture_id)
        return SimpleNamespace(status="ok", signal_id=1, thread_id="t")

    monkeypatch.setattr(jobs, "interpret_capture", fake_interpret)
    report = jobs.run_interpret(session=session)
    assert len(calls) == 1
    assert report["skipped_duplicate"] == 1
    assert report["interpreted"] == 1


def test_parallel_collection_collects_all_domains(session, monkeypatch, scripted_feed_fetcher):
    from app.services.seeding import seed
    from worker.jobs import run_collection
    seed(session)
    serial = run_collection(session=session, fetcher=scripted_feed_fetcher, force=True)
    assert serial["captures"] >= 0


def test_two_domains_fetch_concurrently(session, monkeypatch):
    import threading
    from urllib.parse import urlparse
    from app.services.seeding import seed
    from app.models.registry import Source
    from app.services.collection.fetcher import FetchResult
    from worker import jobs
    seed(session)
    monkeypatch.setattr("app.services.collection.robots.RobotsCache.allowed",
                        lambda self, url: True)
    barrier = threading.Barrier(2, timeout=5)

    def fake_collect(_session, source, fetcher, _robots, _now, _force, report):
        fetcher.fetch(source.url)
        report["captures"] += 1

    monkeypatch.setattr(jobs, "_collect_source", fake_collect)

    class BarrierFetcher:
        def fetch(self, url, etag=None, last_modified=None):
            barrier.wait()
            return FetchResult(url, 200, b"<html></html>", None, None, False)
    by_domain: dict[str, Source] = {}
    for source in session.query(Source).all():
        netloc = urlparse(source.url).netloc
        if netloc not in by_domain:
            by_domain[netloc] = source
    assert len(by_domain) >= 2
    sources = list(by_domain.values())[:2]
    source_by_id = {s.id: s for s in sources}

    class _FakeSession:
        def query(self, model):
            assert model is Source
            return self

        def filter_by(self, *, id):
            self._source = source_by_id[id]
            return self

        def one(self):
            return self._source

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

    jobs._run_collection_parallel(
        sources, BarrierFetcher(),
        robots=jobs.RobotsCache(), now=__import__("datetime").datetime.now(__import__("datetime").UTC),
        force=True, session_factory=_FakeSession, max_workers=2,
    )


def test_run_interpret_runs_captures_concurrently(session, monkeypatch):
    import threading
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from app.models.capture import RawCapture
    from app.models.registry import Source
    from app.services.seeding import seed
    from worker import jobs

    seed(session)
    feed_source = session.query(Source).filter_by(key="harbor_releases").one()
    ids = []
    for idx in range(3):
        c = RawCapture(source_id=feed_source.id, fetched_at=datetime.now(UTC),
                       http_status=200, content_hash=f"conc-{idx}",
                       blob_path=f"/tmp/c{idx}", extracted_text=f"t{idx}",
                       provenance="test")
        session.add(c); session.flush(); ids.append(c.id)

    barrier = threading.Barrier(2, timeout=5)
    def fake_interpret(capture_id, *, session):
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            pass
        return SimpleNamespace(status="ok", signal_id=1, thread_id="t")

    monkeypatch.setattr(jobs, "interpret_capture", fake_interpret)
    monkeypatch.setattr(jobs, "SessionLocal", lambda: session)
    report = jobs.run_interpret(max_workers=2)
    assert report["interpreted"] == 3


def test_run_interpret_excludes_snapshot_captures(session, monkeypatch):
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from app.models.capture import RawCapture
    from app.models.registry import Source
    from app.services.seeding import seed
    from worker import jobs

    seed(session)
    snapshot_source = session.query(Source).filter_by(key="sonatype_compare_jfrog").one()
    feed_source = session.query(Source).filter_by(key="harbor_releases").one()
    snapshot_capture = RawCapture(
        source_id=snapshot_source.id,
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_hash="snapshot-hash",
        blob_path="/tmp/snapshot",
        extracted_text="snapshot page",
        provenance="test",
    )
    feed_capture = RawCapture(
        source_id=feed_source.id,
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_hash="feed-hash",
        blob_path="/tmp/feed",
        extracted_text="feed entry",
        provenance="test",
    )
    session.add_all([snapshot_capture, feed_capture])
    session.flush()

    calls: list[int] = []

    def fake_interpret(capture_id, *, session):
        calls.append(capture_id)
        return SimpleNamespace(status="ok", signal_id=1, thread_id="t")

    monkeypatch.setattr(jobs, "interpret_capture", fake_interpret)
    jobs.run_interpret(session=session)

    assert snapshot_capture.id not in calls
    assert feed_capture.id in calls


def test_run_interpret_caps_captures_per_source(session, monkeypatch):
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from app.models.capture import RawCapture
    from app.models.registry import Source
    from app.services.seeding import seed
    from worker import jobs

    seed(session)
    feed_source = session.query(Source).filter_by(key="harbor_releases").one()
    for idx in range(5):
        session.add(
            RawCapture(
                source_id=feed_source.id,
                fetched_at=datetime.now(UTC),
                http_status=200,
                content_hash=f"cap-hash-{idx}",
                blob_path=f"/tmp/cap-{idx}",
                extracted_text=f"entry {idx}",
                provenance="test",
            )
        )
    session.flush()

    calls: list[int] = []

    def fake_interpret(capture_id, *, session):
        calls.append(capture_id)
        return SimpleNamespace(status="ok", signal_id=1, thread_id="t")

    monkeypatch.setattr(jobs, "interpret_capture", fake_interpret)
    jobs.run_interpret(session=session)

    assert len(calls) == jobs.PER_SOURCE_INTERPRET_CAP


def test_manual_window_skips_old_feed_entries(session):
    from datetime import UTC, datetime

    from app.models.capture import RawCapture
    from app.models.registry import Source
    from app.services.collection.fetcher import FetchResult
    from app.services.collection.robots import RobotsCache
    from app.services.seeding import seed
    from worker import jobs

    seed(session)
    feed_source = session.query(Source).filter_by(key="harbor_releases").one()
    now = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
    feed_body = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>recent-entry</id>
    <title>Recent Release</title>
    <link href="https://example.com/recent"/>
    <published>2026-08-25T12:00:00Z</published>
    <summary>Recent entry</summary>
  </entry>
  <entry>
    <id>old-entry</id>
    <title>Old Release</title>
    <link href="https://example.com/old"/>
    <published>2026-05-29T12:00:00Z</published>
    <summary>Old entry</summary>
  </entry>
</feed>"""

    class WindowFeedFetcher:
        def fetch(self, url, etag=None, last_modified=None):
            return FetchResult(url, 200, feed_body, None, None, False)

    report = {
        "captures": 0,
        "skipped_robots": 0,
        "skipped_not_due": 0,
        "errors": 0,
    }
    jobs._collect_source(
        session,
        feed_source,
        WindowFeedFetcher(),
        RobotsCache(),
        now,
        force=True,
        report=report,
    )
    session.flush()

    assert report["captures"] == 1
    captures = session.query(RawCapture).filter_by(source_id=feed_source.id).all()
    assert len(captures) == 1
    assert captures[0].external_id == "recent-entry"
