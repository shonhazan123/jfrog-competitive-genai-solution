from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ledger import Claim
from app.serializers.common import authored_citation
from app.services.comparison import build_comparison
from app.services.comparison_matrix import build_comparison_matrix, evidence_for_claim


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

        items.append(
            {
                "id": f"bcr_{row.dimension}",
                "dimension": _DIMENSION_LABELS.get(row.dimension, row.dimension),
                "jfrog_position": row.jfrog.text or "",
                "jfrog_citation": authored_citation(),
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
                "evidence": evidence_for_claim(session, claim),
                "no_claim_on_record": no_claim,
            }
        )

    return {"items": items, "total": len(items), "cursor": None}


def list_comparison_matrix(session: Session) -> dict:
    return build_comparison_matrix(session)
