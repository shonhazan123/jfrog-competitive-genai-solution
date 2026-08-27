from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.config.schema import AppConfig
from app.models.capture import RawCapture
from app.models.registry import Entity, Source
from app.models.signal import Signal, SignalEvidence
from app.services.citation import (
    Citation,
    DeliveryRecord,
    build_citation,
    citation_to_dict,
    deliverable,
)
from app.services.scoring.materiality import tier_for


@dataclass
class KitSnippet:
    headline: str
    quote: str
    implication: str
    citation: Citation


@dataclass
class KitRollup:
    key: str
    label: str
    question: str
    category: str
    order: int
    status: str
    count: int
    priority_label: str | None
    snippet: KitSnippet | None
    signal_ids: list[str]
    withheld: int


def _priority_label(score: float, cfg: AppConfig) -> str | None:
    if score <= 0:
        return None
    tier = tier_for(score, cfg)
    return cfg.labels.tiers[tier]


def _signal_max_score(signal: Signal) -> float:
    return max(signal.score_sales, signal.score_product, signal.score_exec)


def _kit_key_for_signal(signal: Signal, cfg: AppConfig, entities: dict[int, Entity]) -> str:
    promote_slug = cfg.kits.promote_to_deal_threats_when.get("subject_entity")
    subject = entities.get(signal.subject_entity_id) if signal.subject_entity_id else None
    if promote_slug and subject and subject.slug == promote_slug:
        return "deal_threats"
    for kit in cfg.kits.kits:
        if signal.signal_type in kit.includes.signal_types:
            return kit.key
    return cfg.kits.kits[0].key


def _delivery_record(
    session: Session,
    signal: Signal,
) -> tuple[DeliveryRecord | None, str]:
    row = (
        session.query(SignalEvidence, RawCapture, Source)
        .join(RawCapture, SignalEvidence.capture_id == RawCapture.id)
        .join(Source, RawCapture.source_id == Source.id)
        .filter(SignalEvidence.signal_id == signal.id)
        .order_by(SignalEvidence.id.asc())
        .first()
    )
    if row:
        sig_ev, capture, source = row
        record = DeliveryRecord(
            source_name=source.key.replace("_", " ").title(),
            source_url=source.url,
            fetched_at=capture.fetched_at,
            provenance=capture.provenance,
            reliability_grade=source.reliability_grade,
        )
        return record, sig_ev.quote

    source = session.get(Source, signal.source_id)
    if source is None:
        return None, signal.headline
    record = DeliveryRecord(
        source_name=source.key.replace("_", " ").title(),
        source_url=source.url,
        fetched_at=signal.occurred_at,
        provenance="extracted",
        reliability_grade=source.reliability_grade,
    )
    return record, signal.headline


def _latest_run_signals(session: Session) -> list[Signal]:
    latest_created = session.query(func.max(Signal.created_at)).scalar()
    if latest_created is None:
        return []
    day_start = latest_created.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    return (
        session.query(Signal)
        .filter(
            Signal.status == "active",
            Signal.created_at >= day_start,
            Signal.created_at < day_end,
        )
        .all()
    )


def roll_up(session: Session, cfg: AppConfig | None = None) -> list[KitRollup]:
    if cfg is None:
        cfg = load_config()

    entities = {entity.id: entity for entity in session.query(Entity).all()}
    signals = _latest_run_signals(session)

    kit_defs = sorted(cfg.kits.kits, key=lambda kit: kit.order)
    buckets: dict[str, list[tuple[Signal, DeliveryRecord, str]]] = {kit.key: [] for kit in kit_defs}
    withheld: dict[str, int] = {kit.key: 0 for kit in kit_defs}

    for signal in signals:
        kit_key = _kit_key_for_signal(signal, cfg, entities)
        record, quote = _delivery_record(session, signal)
        if record is None or not deliverable(record):
            withheld[kit_key] += 1
            continue
        buckets[kit_key].append((signal, record, quote))

    results: list[KitRollup] = []
    for kit_def in kit_defs:
        members = buckets[kit_def.key]
        count = len(members)
        status = "active" if count > 0 else "no_change"
        priority = None
        snippet = None
        signal_ids: list[str] = []

        if members:
            members.sort(key=lambda item: _signal_max_score(item[0]), reverse=True)
            signal_ids = [f"sig_{signal.id}" for signal, _, _ in members]
            lead_signal, lead_record, lead_quote = members[0]
            max_score = _signal_max_score(lead_signal)
            priority = _priority_label(max_score, cfg)
            implication = (
                lead_signal.so_what_sales
                or lead_signal.so_what_product
                or lead_signal.so_what_exec
                or ""
            )
            snippet = KitSnippet(
                headline=lead_signal.headline,
                quote=lead_quote,
                implication=implication,
                citation=build_citation(lead_record),
            )

        results.append(
            KitRollup(
                key=kit_def.key,
                label=kit_def.label,
                question=kit_def.question,
                category=kit_def.category,
                order=kit_def.order,
                status=status,
                count=count,
                priority_label=priority,
                snippet=snippet,
                signal_ids=signal_ids,
                withheld=withheld[kit_def.key],
            )
        )

    return results


def kit_to_dict(kit: KitRollup) -> dict:
    snippet = None
    if kit.snippet is not None:
        snippet = {
            "headline": kit.snippet.headline,
            "quote": kit.snippet.quote,
            "implication": kit.snippet.implication,
            "citation": citation_to_dict(kit.snippet.citation),
        }
    return {
        "key": kit.key,
        "label": kit.label,
        "question": kit.question,
        "category": kit.category,
        "order": kit.order,
        "status": kit.status,
        "count": kit.count,
        "priority_label": kit.priority_label,
        "snippet": snippet,
        "signal_ids": kit.signal_ids,
        "withheld": kit.withheld,
    }
