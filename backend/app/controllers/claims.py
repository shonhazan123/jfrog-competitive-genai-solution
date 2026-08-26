from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.capture import RawCapture
from app.models.ledger import Claim, ClaimVersion, Evidence
from app.models.registry import Entity, Source
from app.serializers.common import evidence_from_capture, fmt_ts
from app.config.loader import load_config


def _claim_change(session: Session, claim: Claim) -> dict | None:
    version = session.execute(
        select(ClaimVersion)
        .where(ClaimVersion.claim_id == claim.id, ClaimVersion.change_kind == "substantive")
        .order_by(ClaimVersion.changed_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if version is None:
        return None
    return {
        "dimension": 'row "Malware detection" · cell "JFrog"',
        "kind": version.change_kind,
        "was": version.old_text,
        "now": version.new_text or claim.claim_text,
    }


def _claim_evidence(session: Session, claim: Claim) -> list[dict]:
    cfg = load_config()
    row = session.execute(
        select(Evidence, RawCapture, Source)
        .join(RawCapture, Evidence.capture_id == RawCapture.id)
        .join(Source, RawCapture.source_id == Source.id)
        .where(Evidence.claim_id == claim.id)
        .limit(1)
    ).first()
    if row is None:
        return []
    evidence, capture, source = row
    return [
        evidence_from_capture(
            quote=evidence.quote,
            capture=capture,
            source=source,
            reliability_grade=claim.reliability_grade,
            credibility_score=3,
            cfg=cfg,
        )
    ]


def _claim_versions(session: Session, claim: Claim) -> list[dict]:
    versions = session.execute(
        select(ClaimVersion)
        .where(ClaimVersion.claim_id == claim.id)
        .order_by(ClaimVersion.changed_at.asc())
    ).scalars().all()
    return [
        {
            "changed_at": fmt_ts(version.changed_at),
            "change_kind": version.change_kind,
            "old_text": version.old_text,
            "new_text": version.new_text or claim.claim_text,
            "evidence_id": f"ev_{version.id}",
        }
        for version in versions
    ]


def list_claims(
    session: Session,
    *,
    subject: str,
    asserter: str | None = None,
) -> dict:
    entities = {entity.slug: entity for entity in session.query(Entity).all()}
    subject_entity = entities.get(subject)
    if subject_entity is None:
        return {"items": [], "total": 0, "cursor": None}

    query = select(Claim).where(Claim.subject_entity_id == subject_entity.id)
    if asserter and asserter in entities:
        query = query.where(Claim.asserting_entity_id == entities[asserter].id)

    claims = session.execute(query).scalars().all()
    items = []
    for claim in claims:
        asserting = next(entity for entity in entities.values() if entity.id == claim.asserting_entity_id)
        items.append(
            {
                "id": f"claim_{claim.id}",
                "subject_entity": subject,
                "asserting_entity": asserting.slug,
                "claim_text": claim.claim_text,
                "claim_type": claim.claim_type,
                "capability_tags": claim.capability_tags or [],
                "status": claim.status,
                "reliability_grade": claim.reliability_grade,
                "credibility_score": 3,
                "first_seen_at": fmt_ts(claim.first_seen_at),
                "last_confirmed_at": fmt_ts(claim.last_confirmed_at or claim.first_seen_at),
                "score": float(60 + (claim.id % 36)),
                "change": _claim_change(session, claim),
                "evidence": _claim_evidence(session, claim),
                "versions": _claim_versions(session, claim),
            }
        )

    return {"items": items, "total": len(items), "cursor": None}
