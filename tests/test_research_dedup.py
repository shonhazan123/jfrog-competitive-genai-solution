from datetime import UTC, datetime

from app.config.schema import ClusterConfig
from app.services.research.dedup import dedupe_items

CFG = ClusterConfig(window_days=3, title_similarity=88)
NOW = datetime(2026, 8, 31, tzinfo=UTC)


def _item(entity, signal_type, headline, at=NOW):
    return {"entity_slug": entity, "signal_type": signal_type, "headline": headline, "occurred_at": at}


def test_near_identical_headlines_merge_into_one_group():
    items = [
        _item("checkmarx", "corporate_financial", "Hellman & Friedman completes acquisition of Checkmarx"),
        _item("checkmarx", "corporate_financial", "Hellman & Friedman completes the acquisition of Checkmarx"),
        _item("checkmarx", "corporate_financial", "Hellman & Friedman completes acquisition of Checkmarx — details"),
    ]
    groups = dedupe_items(items, CFG)
    assert len(groups) == 1
    assert len(groups[0]) == 3


def test_distinct_events_in_same_bucket_stay_separate():
    items = [
        _item("sonatype", "corporate_financial", "Vista Equity Partners acquires majority stake in Sonatype"),
        _item("sonatype", "corporate_financial", "Sonatype launches new SBOM management product line"),
    ]
    groups = dedupe_items(items, CFG)
    assert len(groups) == 2


def test_different_signal_types_never_merge():
    items = [
        _item("snyk", "talent_org", "Snyk hiring senior sales engineers across the org"),
        _item("snyk", "pricing_packaging", "Snyk hiring senior sales engineers across the org"),
    ]
    groups = dedupe_items(items, CFG)
    assert len(groups) == 2


def test_different_entities_never_merge():
    items = [
        _item("snyk", "talent_org", "Company hiring senior sales engineers"),
        _item("aqua", "talent_org", "Company hiring senior sales engineers"),
    ]
    groups = dedupe_items(items, CFG)
    assert len(groups) == 2


def test_representative_is_most_recent():
    older = datetime(2026, 8, 30, tzinfo=UTC)
    newer = datetime(2026, 8, 31, tzinfo=UTC)
    items = [
        _item("aqua", "security_trust", "Aqua advisory on Trivy CVE disclosed", at=older),
        _item("aqua", "security_trust", "Aqua advisory on the Trivy CVE disclosed today", at=newer),
    ]
    groups = dedupe_items(items, CFG)
    assert len(groups) == 1
    assert groups[0][0]["occurred_at"] == newer


def test_empty_input_returns_empty():
    assert dedupe_items([], CFG) == []
