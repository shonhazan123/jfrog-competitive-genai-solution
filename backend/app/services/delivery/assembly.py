from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.config.schema import AppConfig
from app.models.registry import Entity
from app.models.signal import Signal


@dataclass(frozen=True)
class Digest:
    persona: str
    items: list[dict]
    interrupts: list[dict]
    silent_entities: list[str]
    generated_at: datetime


def _persona_score(signal: Signal, persona: str) -> float:
    return getattr(signal, f"score_{persona}")


def _persona_so_what(signal: Signal, persona: str) -> str | None:
    return getattr(signal, f"so_what_{persona}")


def _signal_cvss(signal: Signal) -> float:
    cvss = signal.score_breakdown.get("cvss")
    if isinstance(cvss, (int, float)):
        return float(cvss)
    return 0.0


def _signal_subtype(signal: Signal, corporate_subtypes: list[str]) -> str | None:
    subtype = signal.score_breakdown.get("subtype")
    if isinstance(subtype, str):
        return subtype
    for tag in signal.capability_tags or []:
        if tag in corporate_subtypes:
            return tag
    return None


def _is_interrupt(signal: Signal, cfg: AppConfig, jfrog_entity_id: int | None) -> bool:
    """Interrupt rules from materiality.yaml / ARCHITECTURE §9.

  - cross-assertion: positioning_messaging where subject is JFrog
  - security: security_trust at or above configured CVSS
  - corporate: corporate_financial matching configured subtypes
    """
    interrupt = cfg.materiality.interrupt
    if interrupt.cross_assertion_about_jfrog and jfrog_entity_id is not None:
        if (
            signal.signal_type == "positioning_messaging"
            and signal.subject_entity_id == jfrog_entity_id
        ):
            return True
    if signal.signal_type == "security_trust":
        if _signal_cvss(signal) >= interrupt.security_cvss_at_least:
            return True
    if signal.signal_type == "corporate_financial":
        subtype = _signal_subtype(signal, interrupt.corporate_subtypes)
        if subtype in interrupt.corporate_subtypes:
            return True
    return False


def _signal_to_item(signal: Signal, persona: str, entity_slug: str) -> dict:
    return {
        "signal_id": signal.id,
        "entity": entity_slug,
        "headline": signal.headline,
        "score": _persona_score(signal, persona),
        "so_what": _persona_so_what(signal, persona),
    }


def _apply_diversity_cap(
    signals: list[Signal],
    entity_slug_by_id: dict[int, str],
    max_per_entity: int,
) -> list[Signal]:
    counts: dict[str, int] = {}
    selected: list[Signal] = []
    for signal in signals:
        slug = entity_slug_by_id[signal.entity_id]
        if counts.get(slug, 0) >= max_per_entity:
            continue
        counts[slug] = counts.get(slug, 0) + 1
        selected.append(signal)
    return selected


# Signal types the demo digest tries to lead with, in order, so the main section
# reads as a spread of competitive intel (a feature, a hire, a pricing move)
# rather than a wall of security — security has its own section below.
_DEMO_PREFERRED_TYPES = ("product_capability", "talent_org")


def select_demo_items(
    session: Session, persona: str, limit: int = 3
) -> list[dict]:
    """Curated main section for the demo digest: guarantees one feature
    (product_capability) and one hiring (talent_org) signal when available, then
    fills the rest with the strongest remaining non-security signals, preferring
    types not already shown. Security is excluded here — it has its own section."""
    entity_slug_by_id = {entity.id: entity.slug for entity in session.query(Entity).all()}
    signals = (
        session.query(Signal)
        .filter(Signal.status == "active", Signal.signal_type != "security_trust")
        .all()
    )
    signals.sort(key=lambda s: _persona_score(s, persona), reverse=True)

    selected: list[Signal] = []
    chosen_ids: set[int] = set()

    def take(candidate: Signal) -> None:
        selected.append(candidate)
        chosen_ids.add(candidate.id)

    # 1. Guarantee a feature and a hiring signal, best-scored of each.
    for wanted in _DEMO_PREFERRED_TYPES:
        pick = next(
            (s for s in signals if s.signal_type == wanted and s.id not in chosen_ids),
            None,
        )
        if pick is not None:
            take(pick)

    # 2. Fill remaining slots, preferring a type not already represented.
    for require_new_type in (True, False):
        for signal in signals:
            if len(selected) >= limit:
                break
            if signal.id in chosen_ids:
                continue
            if require_new_type and signal.signal_type in {
                s.signal_type for s in selected
            }:
                continue
            take(signal)

    selected.sort(key=lambda s: _persona_score(s, persona), reverse=True)
    return [
        _signal_to_item(signal, persona, entity_slug_by_id[signal.entity_id])
        for signal in selected[:limit]
    ]


def newest_security_news(session: Session, limit: int = 3) -> list[dict]:
    """Most recent security_trust signals, newest first.

    Backs the demo digest's "latest security news from the industry" section.
    These are the security findings surfaced by the industry research agent."""
    signals = (
        session.query(Signal)
        .filter(Signal.status == "active", Signal.signal_type == "security_trust")
        .order_by(Signal.occurred_at.desc())
        .limit(limit)
        .all()
    )
    entity_slug_by_id = {entity.id: entity.slug for entity in session.query(Entity).all()}
    news: list[dict] = []
    for signal in signals:
        news.append(
            {
                "signal_id": signal.id,
                "entity": entity_slug_by_id.get(signal.entity_id, ""),
                "headline": signal.headline,
                "occurred_on": signal.occurred_at.strftime("%b %d, %Y")
                if signal.occurred_at
                else "",
            }
        )
    return news


def assemble(session: Session, persona: str, cfg: AppConfig, as_of: datetime) -> Digest:
    entities = session.query(Entity).all()
    entity_slug_by_id = {entity.id: entity.slug for entity in entities}
    jfrog_entity_id = next(
        (entity.id for entity in entities if entity.slug == "jfrog"),
        None,
    )

    signals = (
        session.query(Signal)
        .filter(Signal.status == "active")
        .all()
    )

    threshold = cfg.materiality.threshold[persona]
    budget = cfg.materiality.budget[persona]
    max_per_entity = cfg.materiality.max_per_entity

    interrupt_signals = [
        signal for signal in signals if _is_interrupt(signal, cfg, jfrog_entity_id)
    ]
    interrupt_ids = {signal.id for signal in interrupt_signals}
    regular_signals = [signal for signal in signals if signal.id not in interrupt_ids]

    eligible = [
        signal
        for signal in regular_signals
        if _persona_score(signal, persona) >= threshold
    ]
    eligible.sort(key=lambda signal: _persona_score(signal, persona), reverse=True)

    capped = _apply_diversity_cap(eligible, entity_slug_by_id, max_per_entity)
    selected = capped[:budget]

    items = [
        _signal_to_item(signal, persona, entity_slug_by_id[signal.entity_id])
        for signal in selected
    ]
    interrupts = [
        _signal_to_item(signal, persona, entity_slug_by_id[signal.entity_id])
        for signal in interrupt_signals
    ]

    competitor_slugs = {
        entity.slug for entity in cfg.entities if entity.kind == "competitor"
    }
    entity_id_by_slug = {entity.slug: entity.id for entity in entities}
    signaled_entity_ids = {signal.entity_id for signal in signals}
    silent_entities = sorted(
        slug
        for slug in competitor_slugs
        if slug in entity_id_by_slug
        and entity_id_by_slug[slug] not in signaled_entity_ids
    )

    return Digest(
        persona=persona,
        items=items,
        interrupts=interrupts,
        silent_entities=silent_entities,
        generated_at=as_of,
    )
