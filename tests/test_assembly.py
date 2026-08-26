from collections import Counter
from datetime import UTC, datetime

import pytest

from app.config.loader import load_config
from app.models.registry import Entity, Source
from app.models.signal import Signal
from app.services.delivery.assembly import assemble
from app.services.seeding import seed

CFG = load_config()
NOW = datetime.now(UTC)


def _source_for_entity(session, entities: dict[str, Entity], slug: str) -> Source:
    entity = entities[slug]
    source = session.query(Source).filter_by(entity_id=entity.id).first()
    if source is None:
        source = Source(
            key=f"{slug}_fixture",
            entity_id=entity.id,
            url=f"https://example.com/{slug}",
            kind="atom",
            mode="feed",
            reliability_grade="A",
            is_primary=True,
            check_frequency_minutes=360,
        )
        session.add(source)
        session.flush()
    return source


def _add_signal(
    session,
    *,
    source: Source,
    entity: Entity,
    headline: str,
    cluster_key: str,
    score_sales: float,
    score_product: float,
    score_exec: float,
    signal_type: str = "product_capability",
    subject_entity_id: int | None = None,
) -> Signal:
    signal = Signal(
        source_id=source.id,
        entity_id=entity.id,
        subject_entity_id=subject_entity_id,
        signal_type=signal_type,
        headline=headline,
        occurred_at=NOW,
        cluster_key=cluster_key,
        score_sales=score_sales,
        score_product=score_product,
        score_exec=score_exec,
        so_what_sales="sales so what",
        so_what_product="product so what",
        so_what_exec="exec so what",
    )
    session.add(signal)
    session.flush()
    return signal


@pytest.fixture
def many_high_scoring_signals(session):
    seed(session)
    entities = {entity.slug: entity for entity in session.query(Entity).all()}
    competitor_slugs = ["sonatype", "github", "gitlab", "harbor", "azure_artifacts"]
    threshold = CFG.materiality.threshold["sales"]
    score = threshold + 10.0

    signals = []
    for index in range(10):
        slug = competitor_slugs[index % len(competitor_slugs)]
        entity = entities[slug]
        source = _source_for_entity(session, entities, slug)
        signals.append(
            _add_signal(
                session,
                source=source,
                entity=entity,
                headline=f"High-scoring signal {index} from {slug}",
                cluster_key=f"high-{index}",
                score_sales=score,
                score_product=score,
                score_exec=score,
            )
        )
    return signals


@pytest.fixture
def twenty_sonatype_signals(session):
    seed(session)
    entities = {entity.slug: entity for entity in session.query(Entity).all()}
    sonatype = entities["sonatype"]
    source = _source_for_entity(session, entities, "sonatype")
    threshold = CFG.materiality.threshold["product"]
    score = threshold + 10.0

    signals = []
    for index in range(20):
        signals.append(
            _add_signal(
                session,
                source=source,
                entity=sonatype,
                headline=f"Sonatype product signal {index}",
                cluster_key=f"sonatype-{index}",
                score_sales=score,
                score_product=score,
                score_exec=score,
            )
        )
    return signals


@pytest.fixture
def signals_for_sonatype_only(session):
    seed(session)
    entities = {entity.slug: entity for entity in session.query(Entity).all()}
    sonatype = entities["sonatype"]
    source = _source_for_entity(session, entities, "sonatype")
    threshold = CFG.materiality.threshold["product"]
    score = threshold + 10.0

    signals = []
    for index in range(4):
        signals.append(
            _add_signal(
                session,
                source=source,
                entity=sonatype,
                headline=f"Sonatype-only signal {index}",
                cluster_key=f"sonatype-only-{index}",
                score_sales=score,
                score_product=score,
                score_exec=score,
            )
        )
    return signals


@pytest.fixture
def cross_assertion_signal(session):
    seed(session)
    entities = {entity.slug: entity for entity in session.query(Entity).all()}
    sonatype = entities["sonatype"]
    jfrog = entities["jfrog"]
    source = _source_for_entity(session, entities, "sonatype")
    threshold = CFG.materiality.threshold["sales"]
    score = threshold + 10.0

    return _add_signal(
        session,
        source=source,
        entity=sonatype,
        subject_entity_id=jfrog.id,
        signal_type="positioning_messaging",
        headline="Sonatype positions against JFrog",
        cluster_key="cross-assertion",
        score_sales=score,
        score_product=score,
        score_exec=score,
    )


@pytest.fixture
def low_scoring_signals(session):
    seed(session)
    entities = {entity.slug: entity for entity in session.query(Entity).all()}
    sonatype = entities["sonatype"]
    source = _source_for_entity(session, entities, "sonatype")
    threshold = CFG.materiality.threshold["exec"]
    score = threshold - 10.0

    signals = []
    for index in range(4):
        signals.append(
            _add_signal(
                session,
                source=source,
                entity=sonatype,
                headline=f"Low exec signal {index}",
                cluster_key=f"low-exec-{index}",
                score_sales=score,
                score_product=score,
                score_exec=score,
            )
        )
    return signals


def test_the_budget_is_absolute_regardless_of_score(session, many_high_scoring_signals):
    digest = assemble(session, "sales", cfg=CFG, as_of=NOW)
    assert len(digest.items) == CFG.materiality.budget["sales"]


def test_one_busy_competitor_cannot_monopolise_a_digest(session, twenty_sonatype_signals):
    digest = assemble(session, "product", cfg=CFG, as_of=NOW)
    assert max(Counter(i["entity"] for i in digest.items).values()) <= CFG.materiality.max_per_entity


def test_silent_entities_are_a_first_class_output(session, signals_for_sonatype_only):
    digest = assemble(session, "product", cfg=CFG, as_of=NOW)
    assert "harbor" in digest.silent_entities


def test_interrupts_bypass_the_budget(session, cross_assertion_signal, many_high_scoring_signals):
    digest = assemble(session, "sales", cfg=CFG, as_of=NOW)
    assert len(digest.interrupts) == 1
    assert len(digest.items) == CFG.materiality.budget["sales"]


def test_signals_below_the_persona_threshold_are_excluded(session, low_scoring_signals):
    assert assemble(session, "exec", cfg=CFG, as_of=NOW).items == []
