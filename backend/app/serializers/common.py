from __future__ import annotations

from datetime import UTC, datetime

from app.models.capture import RawCapture
from app.models.registry import Entity, Source


def fmt_ts(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def entity_ref(entity: Entity) -> dict:
    tier = None if entity.kind == "industry" else entity.tier
    return {"slug": entity.slug, "name": entity.name, "tier": tier}


def evidence_from_capture(
    *,
    quote: str,
    capture: RawCapture,
    source: Source,
    reliability_grade: str,
    credibility_score: int,
    is_primary: bool = True,
) -> dict:
    return {
        "quote": quote,
        "source_url": source.url,
        "source_name": source.key.replace("_", " ").title(),
        "captured_at": fmt_ts(capture.fetched_at),
        "reliability_grade": reliability_grade,
        "credibility_score": credibility_score,
        "is_primary": is_primary,
    }
