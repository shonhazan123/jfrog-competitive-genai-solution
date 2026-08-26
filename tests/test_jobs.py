from pathlib import Path
import pytest
from app.services.collection.fetcher import FetchResult

ATOM = (Path(__file__).parent / "fixtures" / "nexus_releases.atom").read_bytes()

class DenyRobots:
    def allowed(self, url: str) -> bool:
        return False

@pytest.fixture
def fake_robots_denying():
    return DenyRobots()

class ScriptedFeedFetcher:
    def fetch(self, url, etag=None, last_modified=None):
        return FetchResult(url, 200, ATOM, None, None, False)

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

def test_manual_trigger_calls_the_same_function_the_scheduler_calls():
    """The button is a convenience, not a parallel implementation."""
    import inspect
    from app.controllers.runs import trigger_collection
    assert "run_collection" in inspect.getsource(trigger_collection)
