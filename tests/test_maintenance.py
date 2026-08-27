from datetime import UTC, datetime


def test_reset_findings_clears_signals_and_claims_but_keeps_registry(session):
    from app.models.registry import Entity, Source
    from app.models.signal import Signal
    from app.models.ledger import Claim
    from app.services.seeding import seed
    from app.services.maintenance import reset_findings

    seed(session)
    entity = session.query(Entity).filter_by(slug="sonatype").one()
    source = session.query(Source).filter_by(entity_id=entity.id).first()
    jfrog = session.query(Entity).filter_by(slug="jfrog").one()
    session.add(Signal(
        source_id=source.id, entity_id=entity.id, signal_type="product_capability",
        headline="stale signal", occurred_at=datetime.now(UTC), cluster_key="k1",
    ))
    session.add(Claim(
        subject_entity_id=jfrog.id, asserting_entity_id=entity.id,
        claim_text="stale claim", claim_type="positioning", dimension="artifact_management",
        reliability_grade="C", first_seen_at=datetime.now(UTC),
    ))
    session.flush()

    entities_before = session.query(Entity).count()
    sources_before = session.query(Source).count()

    reset_findings(session)

    assert session.query(Signal).count() == 0
    assert session.query(Claim).count() == 0
    assert session.query(Entity).count() == entities_before
    assert session.query(Source).count() == sources_before
