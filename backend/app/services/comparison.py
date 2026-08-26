from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entity_helpers import entity_by_slug
from app.models.ledger import Claim, ClaimVersion, Evidence

@dataclass(frozen=True)
class ComparisonCell:
    text: str | None
    grade: str | None
    origin: Literal["extracted", "authored", "absent"]
    evidence_id: int | None

@dataclass(frozen=True)
class ComparisonRow:
    dimension: str
    jfrog: ComparisonCell
    competitor: ComparisonCell
    last_changed_at: datetime | None

def build_comparison(session: Session, competitor_slug: str, cfg=None) -> list[ComparisonRow]:
    """Rows are derived, never authored — except JFrog's own column, which is
    authored by definition and marked as such."""
    if cfg is None or cfg is ...:
        from app.config.loader import load_config
        cfg = load_config()
    competitor = entity_by_slug(session, competitor_slug)
    authored = {p.dimension: p.text for p in cfg.jfrog_positions.positions}

    claims = session.execute(
        select(Claim).where(Claim.asserting_entity_id == competitor.id)
    ).scalars().all()
    by_dimension = {c.dimension: c for c in claims if c.dimension}

    rows: list[ComparisonRow] = []
    for dimension, jfrog_text in authored.items():
        claim = by_dimension.get(dimension)

        if claim is None:
            competitor_cell = ComparisonCell(None, None, "absent", None)
            last_changed = None
        else:
            evidence = session.execute(
                select(Evidence).where(Evidence.claim_id == claim.id).limit(1)
            ).scalar_one_or_none()
            competitor_cell = ComparisonCell(
                text=claim.claim_text, grade=claim.reliability_grade,
                origin="extracted", evidence_id=evidence.id if evidence else None,
            )
            last_changed = session.execute(
                select(ClaimVersion.changed_at)
                .where(ClaimVersion.claim_id == claim.id)
                .order_by(ClaimVersion.changed_at.desc()).limit(1)
            ).scalar_one_or_none()

        rows.append(ComparisonRow(
            dimension=dimension,
            jfrog=ComparisonCell(jfrog_text, None, "authored", None),
            competitor=competitor_cell,
            last_changed_at=last_changed,
        ))
    return rows
