from __future__ import annotations

from sqlalchemy.orm import Session

from app.controllers.signals import (
    _entity_map,
    _serialize_signal,
    _signal_evidence,
)
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


def _ranked_active_signals(session: Session, *, limit: int = 5) -> list[Signal]:
    signals = session.query(Signal).filter(Signal.status == "active").all()
    return sorted(signals, key=_overall_score, reverse=True)[:limit]


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
    return {"headline": compose_headline(cards), "cards": cards}
