from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.registry import Entity, Source
from app.serializers.common import fmt_ts

_EXCLUSION_REASONS = {
    "sonatype_devportal": "excluded — blocked by robots.txt",
    "g2_reviews": "excluded — ToS prohibits automated collection (G2)",
}


def _check_frequency(minutes: int | None) -> str | None:
    if minutes is None:
        return None
    if minutes < 120:
        return "1h"
    if minutes < 480:
        return "6h"
    if minutes < 900:
        return "12h"
    return "24h"


def list_sources(session: Session, entity: str | None = None) -> dict:
    entities = {entity_row.id: entity_row for entity_row in session.query(Entity).all()}
    slug_by_id = {row.id: row.slug for row in entities.values()}
    query = session.query(Source)
    if entity:
        entity_row = next((row for row in entities.values() if row.slug == entity), None)
        if entity_row:
            query = query.filter(Source.entity_id == entity_row.id)

    items = []
    for source in query.all():
        excluded = not source.enabled or source.robots_allowed is False
        exclusion_reason = None
        if excluded:
            exclusion_reason = _EXCLUSION_REASONS.get(
                source.key,
                "excluded — blocked by robots.txt" if source.robots_allowed is False else None,
            )
        items.append(
            {
                "id": source.key,
                "name": source.key.replace("_", " ").title(),
                "entity": slug_by_id.get(source.entity_id, "all"),
                "kind": source.kind,
                "mode": source.mode,
                "reliability_grade": source.reliability_grade if source.enabled else None,
                "credibility_score": 2 if source.enabled else None,
                "check_frequency": _check_frequency(source.check_frequency_minutes),
                "robots_allowed": source.robots_allowed if source.robots_allowed is not None else True,
                "requires_js": source.requires_js,
                "last_checked": fmt_ts(source.last_checked_at),
                "enabled": source.enabled,
                "excluded": excluded,
                "exclusion_reason": exclusion_reason,
            }
        )
    return {"items": items, "total": len(items), "cursor": None}


def patch_source(
    session: Session,
    source_id: str,
    *,
    enabled: bool | None,
    actor: str,
    reason: str | None = None,
) -> dict:
    source = session.query(Source).filter_by(key=source_id).one_or_none()
    if source is None:
        raise ValueError(f"Source {source_id} not found")
    if enabled is not None:
        source.enabled = enabled
    session.flush()
    entities = {entity_row.id: entity_row for entity_row in session.query(Entity).all()}
    slug_by_id = {row.id: row.slug for row in entities.values()}
    excluded = not source.enabled or source.robots_allowed is False
    exclusion_reason = None
    if excluded:
        exclusion_reason = _EXCLUSION_REASONS.get(
            source.key,
            "excluded — blocked by robots.txt" if source.robots_allowed is False else None,
        )
    return {
        "id": source.key,
        "name": source.key.replace("_", " ").title(),
        "entity": slug_by_id.get(source.entity_id, "all"),
        "kind": source.kind,
        "mode": source.mode,
        "reliability_grade": source.reliability_grade if source.enabled else None,
        "credibility_score": 2 if source.enabled else None,
        "check_frequency": _check_frequency(source.check_frequency_minutes),
        "robots_allowed": source.robots_allowed if source.robots_allowed is not None else True,
        "requires_js": source.requires_js,
        "last_checked": fmt_ts(source.last_checked_at),
        "enabled": source.enabled,
        "excluded": excluded,
        "exclusion_reason": exclusion_reason,
    }
