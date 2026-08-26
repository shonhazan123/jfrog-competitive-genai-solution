from datetime import UTC
from pathlib import Path
from app.services.collection.feeds import parse_feed
from app.services.signals.novelty import is_new, mark_seen

ATOM = (Path(__file__).parent / "fixtures" / "nexus_releases.atom").read_bytes()

def test_parses_entries_with_stable_ids_and_utc_dates():
    entries = parse_feed(ATOM, "https://github.com/sonatype/nexus-public/releases.atom")
    assert len(entries) == 2
    assert entries[0].external_id == "tag:github.com,2008:Repository/1234/release-3.95.0"
    assert entries[0].published_at.tzinfo is not None
    assert entries[0].published_at.astimezone(UTC).year == 2026

def test_falls_back_to_link_when_no_id_present():
    minimal = b"""<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>t</title><link>https://x.test/a</link></item></channel></rss>"""
    assert parse_feed(minimal, "https://x.test/feed")[0].external_id == "https://x.test/a"

def test_novelty_is_per_source_and_idempotent(session, seeded_source):
    assert is_new(session, seeded_source.id, "abc") is True
    mark_seen(session, seeded_source.id, "abc", capture_id=None)
    assert is_new(session, seeded_source.id, "abc") is False

def test_same_external_id_on_a_different_source_is_still_new(session, seeded_source, second_source):
    mark_seen(session, seeded_source.id, "abc", capture_id=None)
    assert is_new(session, second_source.id, "abc") is True
