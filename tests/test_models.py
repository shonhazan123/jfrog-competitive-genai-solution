from datetime import UTC, datetime
from app.models.registry import Entity, Source
from app.models.ledger import Claim, ClaimVersion

def test_claim_carries_subject_and_asserter_separately(session):
    jfrog = Entity(slug="jfrog", name="JFrog", kind="self", tier=1)
    sona = Entity(slug="sonatype", name="Sonatype", kind="competitor", tier=1)
    session.add_all([jfrog, sona])
    session.flush()

    claim = Claim(
        subject_entity_id=jfrog.id,
        asserting_entity_id=sona.id,
        claim_text="JFrog has hidden costs for storage and transfer",
        claim_type="pricing",
        capability_tags=["pricing_model"],
        reliability_grade="A",
        first_seen_at=datetime.now(UTC),
    )
    session.add(claim)
    session.flush()

    assert claim.subject_entity_id != claim.asserting_entity_id
    assert claim.status == "active"

def test_claim_version_records_a_before_and_after(session, sample_claim):
    version = ClaimVersion(
        claim_id=sample_claim.id,
        old_text="Limited",
        new_text="Very limited, not proactive",
        change_kind="substantive",
        changed_at=datetime.now(UTC),
    )
    session.add(version)
    session.flush()
    assert version.old_text != version.new_text
