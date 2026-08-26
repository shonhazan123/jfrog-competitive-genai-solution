from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.registry import Entity, Source
from app.models.signal import Signal
from app.services.config_overrides import current_config
from app.services.scoring.materiality import score


def _signal_facets(session: Session, signal: Signal, entities: dict[int, Entity]) -> dict:
    source = session.get(Source, signal.source_id)
    entity = entities[signal.entity_id]
    subject_slug = None
    if signal.subject_entity_id:
        subject = entities.get(signal.subject_entity_id)
        subject_slug = subject.slug if subject else None
    return {
        "signal_type": signal.signal_type,
        "subject_entity": subject_slug,
        "asserting_entity": entity.slug,
        "entity_tier": entity.tier,
        "reliability_grade": source.reliability_grade if source else "C",
        "corroboration_count": signal.corroboration_count,
        "capability_tags": signal.capability_tags,
        "occurred_at": signal.occurred_at,
        "text": signal.headline,
    }


def rescore_all_signals(session: Session) -> int:
    config = current_config()
    entities = {entity.id: entity for entity in session.query(Entity).all()}
    updated = 0
    for signal in session.query(Signal).all():
        facets = _signal_facets(session, signal, entities)
        breakdown = {
            persona: score(facets, persona, config).parts
            for persona in ("sales", "product", "exec")
        }
        signal.score_sales = score(facets, "sales", config).total
        signal.score_product = score(facets, "product", config).total
        signal.score_exec = score(facets, "exec", config).total
        signal.score_breakdown = {k: [list(p) for p in v] for k, v in breakdown.items()}
        updated += 1
    session.flush()
    return updated
