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
