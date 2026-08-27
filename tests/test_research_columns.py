from datetime import UTC, datetime


def test_claim_stance_and_signal_theme_key_persist(session):
    from app.models.registry import Entity
    from app.models.ledger import Claim
    from app.models.signal import Signal
    from app.services.seeding import seed

    seed(session)
    jfrog = session.query(Entity).filter_by(slug="jfrog").one()
    sonatype = session.query(Entity).filter_by(slug="sonatype").one()
    source_id = session.query(Entity).filter_by(slug="sonatype").one().id

    claim = Claim(
        subject_entity_id=jfrog.id, asserting_entity_id=sonatype.id,
        claim_text="x", claim_type="positioning", dimension="artifact_management",
        stance="weak", reliability_grade="C", first_seen_at=datetime.now(UTC),
    )
    signal = Signal(
        source_id=source_id, entity_id=sonatype.id, signal_type="security_trust",
        headline="y", occurred_at=datetime.now(UTC), cluster_key="k", theme_key="supply_chain_vulns",
    )
    session.add_all([claim, signal]); session.flush()
    session.refresh(claim); session.refresh(signal)
    assert claim.stance == "weak"
    assert signal.theme_key == "supply_chain_vulns"
