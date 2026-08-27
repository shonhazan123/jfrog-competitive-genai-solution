from datetime import UTC, datetime

import pytest


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
def seeded_malware_claim(session, comparison_entities):
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


def test_xray_row_has_sourced_cell_for_competitor_with_malware_claim(
    session, seeded_malware_claim,
):
    from app.controllers.comparison import list_comparison_matrix

    matrix = list_comparison_matrix(session)
    xray = next(c for c in matrix["components"] if c["key"] == "xray")
    sonatype_cell = next(c for c in xray["cells"] if c["competitor"] == "sonatype")

    assert sonatype_cell["stance"] != "no_claim"
    assert sonatype_cell["evidence"]
