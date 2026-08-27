from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.models.capture import RawCapture
from app.models.registry import Entity, Source
from app.models.signal import Signal, SignalEvidence, AnalystAction
from app.serializers.common import (
    entity_ref,
    evidence_from_capture,
    fmt_ts,
    signal_type_label,
    state_label,
)
from app.services.scoring.materiality import primary_stakeholder, tier_for


def _entity_map(session: Session) -> dict[int, Entity]:
    return {entity.id: entity for entity in session.query(Entity).all()}


def _signal_evidence(session: Session, signal: Signal) -> list[dict]:
    cfg = load_config()
    rows = session.execute(
        select(SignalEvidence, RawCapture, Source)
        .join(RawCapture, SignalEvidence.capture_id == RawCapture.id)
        .join(Source, RawCapture.source_id == Source.id)
        .where(SignalEvidence.signal_id == signal.id)
    ).all()
    if not rows:
        source = session.get(Source, signal.source_id)
        from app.services.citation import DeliveryRecord, build_citation, citation_to_dict

        record = DeliveryRecord(
            source_name=source.key.replace("_", " ").title() if source else "unknown",
            source_url=source.url if source else "",
            fetched_at=signal.occurred_at,
            provenance="extracted",
            reliability_grade=source.reliability_grade if source else "A",
        )
        return [
            {
                "quote": signal.headline,
                "source_url": source.url if source else "",
                "source_name": source.key if source else "unknown",
                "captured_at": fmt_ts(signal.occurred_at),
                "reliability_grade": "A",
                "credibility_score": 2,
                "is_primary": True,
                "citation": citation_to_dict(build_citation(record)),
            }
        ]
    evidence = []
    for idx, (sig_ev, capture, source) in enumerate(rows):
        evidence.append(
            evidence_from_capture(
                quote=sig_ev.quote,
                capture=capture,
                source=source,
                reliability_grade=source.reliability_grade,
                credibility_score=2,
                is_primary=idx == 0,
                cfg=cfg,
            )
        )
    return evidence


def _serialize_signal(
    signal: Signal,
    entities: dict[int, Entity],
    persona: str | None,
) -> dict:
    cfg = load_config()
    entity = entities[signal.entity_id]
    subject = entities.get(signal.subject_entity_id) if signal.subject_entity_id else None
    asserting = entities.get(entity.id)
    breakdown = signal.score_breakdown or {}

    flavour = None
    if signal.signal_type == "positioning_messaging":
        flavour = breakdown.get("flavour")

    active_persona = persona or "sales"
    scores = {
        "sales": float(signal.score_sales),
        "product": float(signal.score_product),
        "exec": float(signal.score_exec),
    }
    stakeholder = primary_stakeholder(scores)
    tier = tier_for(scores[active_persona], cfg)
    return {
        "id": f"sig_{signal.id}",
        "entity": entity_ref(entity),
        "signal_type": signal.signal_type,
        "signal_type_label": signal_type_label(signal.signal_type, cfg),
        "signal_flavour": flavour,
        "subject_entity": subject.slug if subject else None,
        "asserting_entity": asserting.slug if asserting else entity.slug,
        "mentions_jfrog": bool(subject and subject.slug == "jfrog"),
        "headline": signal.headline,
        "occurred_at": fmt_ts(signal.occurred_at),
        "persona": active_persona,
        "so_what": getattr(signal, f"so_what_{active_persona}") or "",
        "tier": tier,
        "tier_label": cfg.labels.tiers[tier],
        "primary_stakeholder": stakeholder,
        "why_it_matters": signal.why_it_matters or "",
        "handling": signal.handling,
        "handling_label": state_label(signal.handling, cfg),
        "awareness_only": bool(breakdown.get("awareness_only")),
        "evidence": [],
        "cluster_id": signal.cluster_key,
        "corroboration_count": signal.corroboration_count,
        "interrupt_tier": breakdown.get("interrupt_tier"),
    }


def list_signals(
    session: Session,
    *,
    persona: str | None = None,
    entity: str | None = None,
    signal_type: str | None = None,
    limit: int = 50,
) -> dict:
    entities = _entity_map(session)
    slug_to_id = {entity.slug: entity.id for entity in entities.values()}
    query = session.query(Signal).filter(Signal.status == "active")
    if entity and entity in slug_to_id:
        query = query.filter(Signal.entity_id == slug_to_id[entity])
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    signals = query.order_by(Signal.occurred_at.desc()).limit(limit).all()
    items = []
    for signal in signals:
        row = _serialize_signal(signal, entities, persona)
        row["evidence"] = _signal_evidence(session, signal)
        items.append(row)
    return {"items": items, "total": len(items), "cursor": None}


def create_action(
    session: Session,
    signal_id: int,
    *,
    action: str,
    actor: str,
    reason: str | None = None,
    edit: dict | None = None,
    relevance_adjustment: int | None = None,
) -> dict:
    signal = session.get(Signal, signal_id)
    if signal is None:
        raise ValueError(f"Signal {signal_id} not found")
    row = AnalystAction(
        target_type="signal",
        target_id=signal_id,
        actor=actor,
        action=action,
        reason=reason,
    )
    session.add(row)
    session.flush()
    if edit:
        for field, value in edit.items():
            if hasattr(signal, field):
                setattr(signal, field, value)
    if relevance_adjustment is not None:
        persona_scores = ("score_sales", "score_product", "score_exec")
        for score_field in persona_scores:
            setattr(signal, score_field, getattr(signal, score_field) + relevance_adjustment)
    session.flush()
    return {
        "id": f"act_{row.id}",
        "target_type": "signal",
        "target_id": str(signal_id),
        "action": action,
        "actor": actor,
        "at": fmt_ts(row.created_at),
    }
