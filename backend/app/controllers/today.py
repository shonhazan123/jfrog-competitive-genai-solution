from __future__ import annotations

from collections import defaultdict
from typing import Callable, Hashable, TypeVar

from sqlalchemy.orm import Session

from app.controllers.signals import (
    _entity_map,
    _serialize_signal,
    _signal_evidence,
)
from app.models.registry import Entity
from app.models.signal import Signal
from app.services.industry_themes import theme_label_map
from app.services.scoring.materiality import primary_stakeholder
from app.services.today_brief import compose_headline

T = TypeVar("T")

# The order competitor kinds surface in on the Today rail. Hiring leads to match
# the client rail; the rest follow the product's default reading order. Anything
# not listed keeps its natural order after these.
_CARD_TYPE_ORDER: list[str] = [
    "talent_org",
    "pricing_packaging",
    "product_capability",
    "security_trust",
    "corporate_financial",
    "positioning_messaging",
    "partnership_ecosystem",
    "customer_evidence",
    "market_regulatory",
]


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


def _diversify(
    signals: list[T],
    *,
    group_of: Callable[[T], str],
    order: list[str],
    per_group: int,
    total: int,
    collapse_key: Callable[[T], Hashable] | None = None,
    score: Callable[[T], float] = _overall_score,
) -> list[T]:
    """Pick a varied, non-repetitive set of signals.

    - ``collapse_key`` (optional): keep only the best-scored signal per key, so a
      single rival's near-duplicate posts (same entity + kind) collapse to one
      card instead of stacking three near-identical headlines in one group.
    - Round-robin across groups in ``order`` so several *kinds* of signal are
      represented rather than one high-scoring type crowding out the rest.
    - ``per_group`` caps depth within a group; ``total`` caps the whole set.
    """
    pool = list(signals)
    if collapse_key is not None:
        best: dict[Hashable, T] = {}
        for item in pool:
            key = collapse_key(item)
            if key not in best or score(item) > score(best[key]):
                best[key] = item
        pool = list(best.values())

    by_group: dict[str, list[T]] = defaultdict(list)
    for item in pool:
        by_group[group_of(item)].append(item)
    for bucket in by_group.values():
        bucket.sort(key=score, reverse=True)

    ordered_groups = [g for g in order if g in by_group]
    ordered_groups += [g for g in by_group if g not in ordered_groups]

    picked: list[T] = []
    for depth in range(per_group):
        for group in ordered_groups:
            bucket = by_group[group]
            if depth < len(bucket):
                picked.append(bucket[depth])
                if len(picked) >= total:
                    return picked
    return picked


def _type_rank(signal_type: str) -> int:
    try:
        return _CARD_TYPE_ORDER.index(signal_type)
    except ValueError:
        return len(_CARD_TYPE_ORDER)


def _ranked_active_signals(
    session: Session, *, per_type: int = 3, total: int = 12
) -> list[Signal]:
    """A varied slice of competitor signals for Today: at most one card per
    (competitor, kind) so duplicates collapse, spread across kinds so the brief
    shows Hiring, Pricing, Product, Security … rather than one type on repeat."""
    selected = _diversify(
        _competitor_signals(session),
        group_of=lambda s: s.signal_type,
        order=_CARD_TYPE_ORDER,
        per_group=per_type,
        total=total,
        collapse_key=lambda s: (s.entity_id, s.signal_type),
    )
    # Present in canonical kind order (best-first within each kind) so the brief
    # reads the same way the client rail groups it.
    selected.sort(key=lambda s: (_type_rank(s.signal_type), -_overall_score(s)))
    return selected


def _industry_radar(session: Session, *, per_theme: int = 2, total: int = 8) -> list[dict]:
    """Industry / DevSecOps items relevant to JFrog, grouped the way the Industry
    page groups them — by theme bucket (supply-chain, AI security, pipeline,
    regulation …), not by raw signal type. Each item carries a plain summary and
    a 'why it matters' line so Today carries the field, not just rivals."""
    signals = (
        session.query(Signal)
        .join(Entity, Signal.entity_id == Entity.id)
        .filter(Signal.status == "active", Entity.kind == "industry")
        .order_by(Signal.occurred_at.desc())
        .all()
    )
    labels = theme_label_map()
    order = list(labels.keys())

    def theme_of(signal: Signal) -> str:
        key = getattr(signal, "theme_key", None)
        return key if key in labels else "other"

    ranked = _diversify(
        signals,
        group_of=theme_of,
        order=order,
        per_group=per_theme,
        total=total,
    )

    items: list[dict] = []
    for signal in ranked:
        key = theme_of(signal)
        evidence = _signal_evidence(session, signal)
        items.append(
            {
                "id": f"ind_{signal.id}",
                "signal_type": signal.signal_type,
                "theme_key": key,
                "theme_label": labels.get(key, "Other"),
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
    ranked = _ranked_active_signals(session)
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
