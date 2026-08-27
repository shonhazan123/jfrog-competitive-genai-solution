from __future__ import annotations

from sqlalchemy.orm import Session

from app.controllers.signals import (
    _entity_map,
    _serialize_signal,
    _signal_evidence,
)
from app.models.registry import Entity
from app.models.signal import Signal
from app.services.scoring.materiality import primary_stakeholder
from app.services.today_brief import compose_headline


def _overall_score(signal: Signal) -> float:
    scores = {
        "sales": float(signal.score_sales),
        "product": float(signal.score_product),
        "exec": float(signal.score_exec),
    }
    stakeholder = primary_stakeholder(scores)
    return scores[stakeholder]


def _competitor_signals(session: Session) -> list[Signal]:
    """Active signals about a competitor. Excludes self (JFrog) — JFrog's own
    positioning is authored config, never a card — and industry, which gets its
    own strip below."""
    return (
        session.query(Signal)
        .join(Entity, Signal.entity_id == Entity.id)
        .filter(Signal.status == "active", Entity.kind == "competitor")
        .all()
    )


def _ranked_active_signals(session: Session, *, limit: int = 5) -> list[Signal]:
    return sorted(_competitor_signals(session), key=_overall_score, reverse=True)[:limit]


def _industry_radar(session: Session, *, limit: int = 4) -> list[dict]:
    """Industry / DevSecOps items relevant to JFrog — summarised, each with a
    plain 'why it matters' line — so Today carries the field, not just rivals."""
    signals = (
        session.query(Signal)
        .join(Entity, Signal.entity_id == Entity.id)
        .filter(Signal.status == "active", Entity.kind == "industry")
        .order_by(Signal.occurred_at.desc())
        .all()
    )
    ranked = sorted(signals, key=_overall_score, reverse=True)[:limit]
    items: list[dict] = []
    for signal in ranked:
        evidence = _signal_evidence(session, signal)
        items.append(
            {
                "id": f"ind_{signal.id}",
                "signal_type": signal.signal_type,
                "headline": signal.headline,
                "summary": signal.so_what_exec or signal.so_what_product or signal.headline,
                "why_it_matters": signal.why_it_matters,
                "occurred_at": signal.occurred_at.isoformat() if signal.occurred_at else None,
                "evidence": evidence[:1],
            }
        )
    return items


def get_today(session: Session) -> dict:
    entities = _entity_map(session)
    ranked = _ranked_active_signals(session, limit=5)
    cards: list[dict] = []
    for signal in ranked:
        scores = {
            "sales": float(signal.score_sales),
            "product": float(signal.score_product),
            "exec": float(signal.score_exec),
        }
        stakeholder = primary_stakeholder(scores)
        row = _serialize_signal(signal, entities, stakeholder)
        row["evidence"] = _signal_evidence(session, signal)
        cards.append(row)
    return {
        "headline": compose_headline(cards),
        "cards": cards,
        "industry": _industry_radar(session),
    }
