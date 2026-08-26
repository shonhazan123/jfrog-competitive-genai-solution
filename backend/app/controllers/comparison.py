from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.capture import RawCapture
from app.models.ledger import Claim, ClaimVersion, Evidence
from app.models.registry import Source
from app.serializers.common import evidence_from_capture, fmt_ts
from app.services.comparison import build_comparison


_DIMENSION_LABELS = {
    "malware_detection": "Malware detection",
    "sbom": "SBOM",
    "pricing_model": "Pricing model",
    "package_format_support": "Package format coverage",
    "model_registry": "AI / model artifacts",
    "runtime_security": "Runtime security",
    "deployment_model": "SaaS / self-hosted",
}


def _claim_ids_for_dimension(session: Session, competitor_id: int, dimension: str) -> list[str]:
    claims = session.execute(
        select(Claim).where(
            Claim.asserting_entity_id == competitor_id,
            Claim.dimension == dimension,
        )
    ).scalars().all()
    return [f"claim_{claim.id}" for claim in claims]


def _evidence_for_claim(session: Session, claim: Claim | None) -> list[dict]:
    if claim is None:
        return []
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
        )
    ]


def _change_for_claim(session: Session, claim: Claim | None, dimension: str) -> dict | None:
    if claim is None:
        return None
    version = session.execute(
        select(ClaimVersion)
        .where(ClaimVersion.claim_id == claim.id, ClaimVersion.change_kind == "substantive")
        .order_by(ClaimVersion.changed_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if version is None:
        return None
    label = _DIMENSION_LABELS.get(dimension, dimension)
    return {
        "dimension": f'row "{label}" · cell "JFrog"',
        "kind": version.change_kind,
        "was": version.old_text or "",
        "now": version.new_text or claim.claim_text,
    }


def list_comparison(session: Session, competitor: str = "sonatype") -> dict:
    from app.models.entity_helpers import entity_by_slug

    rows = build_comparison(session, competitor)
    competitor_entity = entity_by_slug(session, competitor)
    claims = {
        claim.dimension: claim
        for claim in session.execute(
            select(Claim).where(Claim.asserting_entity_id == competitor_entity.id)
        ).scalars().all()
        if claim.dimension
    }

    items = []
    for row in rows:
        claim = claims.get(row.dimension)
        no_claim = row.competitor.origin == "absent"
        changed_recently = False
        if row.last_changed_at:
            changed_recently = row.last_changed_at >= datetime.now(UTC) - timedelta(days=7)

        items.append(
            {
                "id": f"bcr_{row.dimension}",
                "dimension": _DIMENSION_LABELS.get(row.dimension, row.dimension),
                "jfrog_position": row.jfrog.text or "",
                "competitor_position": row.competitor.text or (
                    "Positions at build/proxy stage; no runtime claim on record"
                    if no_claim
                    else ""
                ),
                "competitor": competitor,
                "supporting_claim_ids": _claim_ids_for_dimension(
                    session, competitor_entity.id, row.dimension
                ),
                "reliability_grade": row.competitor.grade if not no_claim else "C",
                "credibility_score": 4 if no_claim else 2,
                "last_changed_at": fmt_ts(row.last_changed_at),
                "changed_recently": changed_recently,
                "evidence": _evidence_for_claim(session, claim),
                "change": _change_for_claim(session, claim, row.dimension),
                "no_claim_on_record": no_claim,
            }
        )

    return {"items": items, "total": len(items), "cursor": None}
