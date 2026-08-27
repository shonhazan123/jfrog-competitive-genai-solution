from datetime import UTC, datetime

import pytest

from app.services.comparison import build_comparison


@pytest.fixture(autouse=True)
def comparison_entities(session):
    from app.models.registry import Entity

    entities = [
        Entity(slug="jfrog", name="JFrog", kind="self", tier=1),
        Entity(slug="sonatype", name="Sonatype", kind="competitor", tier=1),
        Entity(slug="harbor", name="Harbor", kind="competitor", tier=2),
    ]
    session.add_all(entities)
    session.flush()
    return {e.slug: e for e in entities}


@pytest.fixture
def seeded_claims(session, comparison_entities):
    from app.models.capture import RawCapture
    from app.models.ledger import Claim, Evidence
    from app.models.registry import Source

    jfrog = comparison_entities["jfrog"]
    sonatype = comparison_entities["sonatype"]

    source = Source(
        key="sonatype_test_source",
        entity_id=sonatype.id,
        url="https://example.com/compare",
        kind="html_page",
        mode="snapshot",
        reliability_grade="B",
        is_primary=True,
        check_frequency_minutes=60,
        requires_js=False,
        covers=["malware_detection"],
    )
    session.add(source)
    session.flush()

    capture = RawCapture(
        source_id=source.id,
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_hash="deadbeef",
        blob_path="/tmp/test",
        extracted_text="Advanced malware detection protects your supply chain.",
        provenance="live",
    )
    session.add(capture)
    session.flush()

    claim = Claim(
        subject_entity_id=jfrog.id,
        asserting_entity_id=sonatype.id,
        claim_text="Sonatype provides advanced malware detection.",
        claim_type="capability",
        capability_tags=["malware_detection"],
        dimension="malware_detection",
        status="active",
        reliability_grade="B",
        first_seen_at=datetime.now(UTC),
    )
    session.add(claim)
    session.flush()

    evidence = Evidence(
        claim_id=claim.id,
        capture_id=capture.id,
        quote="Advanced malware detection",
        quote_offset=0,
    )
    session.add(evidence)
    session.flush()


@pytest.fixture
def seeded_claims_with_history(session, seeded_claims):
    from app.models.ledger import Claim, ClaimVersion

    claim = (
        session.query(Claim)
        .filter_by(dimension="malware_detection")
        .one()
    )
    session.add(
        ClaimVersion(
            claim_id=claim.id,
            old_text="Earlier malware detection wording.",
            new_text=claim.claim_text,
            change_kind="update",
            changed_at=datetime.now(UTC),
        )
    )
    session.flush()


def test_competitor_cells_carry_a_grade_and_evidence(session, seeded_claims):
    rows = build_comparison(session, "sonatype", cfg=...)
    row = next(r for r in rows if r.dimension == "malware_detection")
    assert row.competitor.origin == "extracted"
    assert row.competitor.grade is not None
    assert row.competitor.evidence_id is not None

def test_jfrog_cells_are_authored_and_carry_no_grade(session, seeded_claims):
    """There is no capture to verify authored text against. Grading it would be
    the same unfounded confidence the system exists to prevent."""
    row = build_comparison(session, "sonatype", cfg=...)[0]
    assert row.jfrog.origin == "authored"
    assert row.jfrog.grade is None

def test_a_dimension_with_no_competitor_claim_is_absent_not_graded(session, seeded_claims):
    """G7: the pipeline records what a source says, not that a claim is absent."""
    rows = build_comparison(session, "sonatype", cfg=...)
    row = next(r for r in rows if r.dimension == "runtime_security")
    assert row.competitor.origin == "absent"
    assert row.competitor.grade is None
    assert row.competitor.text is None

def test_recently_changed_rows_expose_their_change_time(session, seeded_claims_with_history):
    rows = build_comparison(session, "sonatype", cfg=...)
    changed = [r for r in rows if r.last_changed_at is not None]
    assert changed


def test_list_comparison_rows_omit_change_detection(session, seeded_claims_with_history):
    from app.controllers.comparison import list_comparison

    result = list_comparison(session, "sonatype")
    assert result["items"]
    for item in result["items"]:
        assert "changed_recently" not in item
        assert "last_changed_at" not in item
        assert "change" not in item


def test_every_dimension_in_config_appears_even_with_no_claims(session):
    rows = build_comparison(session, "harbor", cfg=...)
    assert len(rows) >= 6
