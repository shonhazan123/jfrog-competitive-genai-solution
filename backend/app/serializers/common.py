from __future__ import annotations

from datetime import UTC, datetime

from app.config.loader import load_config
from app.config.schema import AppConfig
from app.models.capture import RawCapture
from app.models.registry import Entity, Source
from app.services.citation import DeliveryRecord, build_citation, citation_to_dict


def fmt_ts(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def entity_ref(entity: Entity) -> dict:
    tier = None if entity.kind == "industry" else entity.tier
    return {"slug": entity.slug, "name": entity.name, "tier": tier}


def _labels_cfg(cfg: AppConfig | None = None) -> AppConfig:
    return cfg or load_config()


def signal_type_label(signal_type: str, cfg: AppConfig | None = None) -> str:
    labels = _labels_cfg(cfg).labels.signal_types
    return labels.get(signal_type, signal_type)


def state_label(state: str | None, cfg: AppConfig | None = None) -> str | None:
    if state is None:
        return None
    return _labels_cfg(cfg).labels.states.get(state)


def evidence_from_capture(
    *,
    quote: str,
    capture: RawCapture,
    source: Source,
    reliability_grade: str,
    credibility_score: int,
    is_primary: bool = True,
    cfg: AppConfig | None = None,
) -> dict:
    record = DeliveryRecord(
        source_name=source.key.replace("_", " ").title(),
        source_url=source.url,
        fetched_at=capture.fetched_at,
        provenance=capture.provenance,
        reliability_grade=reliability_grade,
    )
    citation = build_citation(record)
    return {
        "quote": quote,
        "source_url": source.url,
        "source_name": source.key.replace("_", " ").title(),
        "captured_at": fmt_ts(capture.fetched_at),
        "reliability_grade": reliability_grade,
        "credibility_score": credibility_score,
        "is_primary": is_primary,
        "citation": citation_to_dict(citation),
    }


def authored_citation(source_name: str = "CI team", cfg: AppConfig | None = None) -> dict:
    record = DeliveryRecord(
        source_name=source_name,
        source_url="",
        fetched_at=datetime.now(UTC),
        origin="authored",
    )
    return citation_to_dict(build_citation(record))
