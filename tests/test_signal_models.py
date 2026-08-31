from datetime import UTC, datetime
from app.models.signal import Signal, SignalEvidence

def test_signal_stores_a_score_and_so_what_per_persona(session, seeded_source):
    signal = Signal(
        source_id=seeded_source.id, entity_id=seeded_source.entity_id,
        signal_type="product_capability", headline="Nexus 3.95 adds Cargo registry support",
        occurred_at=datetime.now(UTC), cluster_key="x",
        score_sales=32.0, score_product=71.0, score_exec=18.0,
        so_what_sales="…", so_what_product="…", so_what_exec="…",
        score_breakdown={"sales": [["base", 20.0]], "product": [["base", 30.0]], "exec": [["base", 10.0]]},
        capability_tags=["package_format_support"],
    )
    session.add(signal); session.flush()
    assert signal.score_product > signal.score_sales
    assert signal.status == "active"

def test_signal_subject_defaults_to_none_not_jfrog(session, seeded_source):
    """Most signals are self-assertions. Nothing may presume JFrog is the subject."""
    signal = Signal(
        source_id=seeded_source.id, entity_id=seeded_source.entity_id,
        signal_type="product_capability", headline="h", occurred_at=datetime.now(UTC),
        cluster_key="y", capability_tags=[],
    )
    session.add(signal); session.flush()
    assert signal.subject_entity_id is None
