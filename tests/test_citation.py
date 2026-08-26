from datetime import UTC, datetime

import pytest

from app.config.loader import load_config
from app.services.citation import build_citation, deliverable, DeliveryRecord


@pytest.fixture
def signal_missing_url():
    return DeliveryRecord(
        source_name="Broken source",
        source_url="",
        fetched_at=datetime(2026, 8, 26, tzinfo=UTC),
    )


@pytest.fixture
def archive_signal():
    return DeliveryRecord(
        source_name="Archive capture",
        source_url="https://example.com/page",
        fetched_at=datetime(2026, 8, 26, 6, 0, tzinfo=UTC),
        provenance="archive",
        reliability_grade="B",
    )


def test_a_signal_without_a_source_url_is_never_delivered(signal_missing_url):
    assert deliverable(signal_missing_url) is False


def test_archived_captures_expose_both_a_live_and_an_archived_link(archive_signal):
    citation = build_citation(archive_signal)
    assert citation.source_url and citation.archived_url
    assert "web.archive.org" in citation.archived_url
