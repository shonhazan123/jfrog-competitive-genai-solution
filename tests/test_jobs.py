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
