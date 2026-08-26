from datetime import UTC, datetime, timedelta

import pytest

from app.config.loader import load_config
from app.models.capture import RawCapture
from app.models.registry import Entity, Source
from app.models.signal import Signal, SignalEvidence
from app.services.kits import roll_up
from app.services.seeding import seed

CFG = load_config()
LATEST_RUN_SIGNAL_COUNT = 6

_SIGNAL_TYPE_LABELS = CFG.labels.signal_types


def _make_signal(
    session,
    *,
    entity: Entity,
    source: Source,
    signal_type: str,
    headline: str,
    created_at: datetime,
    subject_entity: Entity | None = None,
    handling: str | None = None,
    score: float = 70.0,
    cluster_key: str = "fixture",
) -> Signal:
    signal = Signal(
        source_id=source.id,
        entity_id=entity.id,
        subject_entity_id=subject_entity.id if subject_entity else None,
        signal_type=signal_type,
        headline=headline,
        occurred_at=created_at,
        cluster_key=cluster_key,
        score_sales=score,
        score_product=score,
        score_exec=score,
        so_what_sales="Sales framing.",
        so_what_product="Product framing.",
        so_what_exec="Executive framing.",
        handling=handling,
        created_at=created_at,
    )
    session.add(signal)
    session.flush()
    capture = RawCapture(
        source_id=source.id,
        fetched_at=created_at,
        http_status=200,
        content_hash=f"hash-{signal.id}",
        blob_path=f"/tmp/{signal.id}.txt",
        extracted_text=headline,
    )
    session.add(capture)
    session.flush()
    session.add(
        SignalEvidence(
            signal_id=signal.id,
            capture_id=capture.id,
            quote=headline,
            quote_offset=0,
            match_method="exact",
        )
    )
    session.flush()
    return signal


@pytest.fixture
def signal_entities(session):
    seed(session)
    entities = {entity.slug: entity for entity in session.query(Entity).all()}
    sonatype_source = session.query(Source).filter_by(key="sonatype_compare_jfrog").one()
    return entities, sonatype_source


@pytest.fixture
def seeded_signals(session, signal_entities):
    entities, source = signal_entities
    run_day = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    specs = [
        ("security_trust", "Advisory affecting Nexus", 78.0, entities.get("jfrog")),
        ("product_capability", "Nexus adds Cargo registry support", 66.0, None),
        ("customer_evidence", "New financial-services case study", 62.0, None),
        ("partnership_ecosystem", "Cloud marketplace listing", 51.0, None),
        ("market_regulatory", "EU CRA reporting obligations dated", 44.0, None),
        ("corporate_financial", "Quarterly revenue beat", 40.0, None),
    ]
    for index, (signal_type, headline, score, subject) in enumerate(specs):
        _make_signal(
            session,
            entity=entities["sonatype"],
            source=source,
            signal_type=signal_type,
            headline=headline,
            created_at=run_day + timedelta(hours=index),
            subject_entity=subject,
            score=score,
            cluster_key=f"seeded-{index}",
        )
    session.flush()
    return run_day


@pytest.fixture
def signals_across_two_runs(session, signal_entities):
    entities, source = signal_entities
    old_day = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    new_day = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    old_types = ["talent_org", "positioning_messaging", "pricing_packaging"]
    for index, signal_type in enumerate(old_types):
        _make_signal(
            session,
            entity=entities["sonatype"],
            source=source,
            signal_type=signal_type,
            headline=f"Old run signal {index}",
            created_at=old_day + timedelta(hours=index),
            cluster_key=f"old-{index}",
            score=30.0,
        )
    new_specs = [
        ("security_trust", "Advisory affecting Nexus", 78.0),
        ("product_capability", "Nexus adds Cargo registry support", 66.0),
        ("customer_evidence", "New financial-services case study", 62.0),
        ("partnership_ecosystem", "Cloud marketplace listing", 51.0),
        ("market_regulatory", "EU CRA reporting obligations dated", 44.0),
        ("corporate_financial", "Quarterly revenue beat", 40.0),
    ]
    for index, (signal_type, headline, score) in enumerate(new_specs):
        _make_signal(
            session,
            entity=entities["sonatype"],
            source=source,
            signal_type=signal_type,
            headline=headline,
            created_at=new_day + timedelta(hours=index),
            cluster_key=f"new-{index}",
            score=score,
        )
    session.flush()


@pytest.fixture
def sparse_signals(session, signal_entities):
    entities, source = signal_entities
    run_day = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    _make_signal(
        session,
        entity=entities["sonatype"],
        source=source,
        signal_type="product_capability",
        headline="Single capability signal",
        created_at=run_day,
        cluster_key="sparse-1",
    )
    session.flush()


def test_every_signal_type_belongs_to_exactly_one_kit():
    config = load_config()
    membership = [t for kit in config.kits.kits for t in kit.includes.signal_types]
    assert sorted(membership) == sorted(set(membership))
    assert set(membership) == set(config.signal_types.types)


def test_kits_roll_up_the_latest_run_only(session, signals_across_two_runs):
    kits = roll_up(session, cfg=CFG)
    total = sum(k.count for k in kits)
    assert total == LATEST_RUN_SIGNAL_COUNT


def test_a_quiet_kit_reports_no_change_rather_than_being_omitted(session, sparse_signals):
    kits = roll_up(session, cfg=CFG)
    assert len(kits) == 6
    quiet = [k for k in kits if k.count == 0]
    assert quiet and all(k.status == "no_change" for k in quiet)


def test_each_kit_carries_a_snippet_with_a_citation(session, seeded_signals):
    kit = next(k for k in roll_up(session, cfg=CFG) if k.count > 0)
    assert kit.snippet.headline
    assert kit.snippet.citation.source_url.startswith("http")


def test_every_enum_value_has_a_human_label():
    config = load_config()
    for value in config.signal_types.types:
        assert config.labels.signal_types[value]
        assert "_" not in config.labels.signal_types[value]
