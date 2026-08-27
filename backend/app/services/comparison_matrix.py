from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.models.capture import RawCapture
from app.models.ledger import Claim, Evidence
from app.models.registry import Entity, Source
from app.serializers.common import evidence_from_capture
from app.settings import settings

_NO_CLAIM_SUMMARY = "No public claim on record."


def _load_components() -> list[dict]:
    data = yaml.safe_load(
        (Path(settings.config_dir) / "jfrog_components.yaml").read_text(encoding="utf-8")
    )
    return data["components"]


def evidence_for_claim(session: Session, claim: Claim | None) -> list[dict]:
    if claim is None:
        return []
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


def _jfrog_position_for_dimension(dimension: str) -> str:
    cfg = load_config()
    for position in cfg.jfrog_positions.positions:
        if position.dimension == dimension:
            return position.text or ""
    return ""


def _claim_for_component(
    session: Session,
    competitor_id: int,
    dimensions: list[str],
) -> Claim | None:
    claims = session.execute(
        select(Claim).where(
            Claim.asserting_entity_id == competitor_id,
            Claim.dimension.in_(dimensions),
        )
    ).scalars().all()
    by_dimension = {claim.dimension: claim for claim in claims if claim.dimension}
    for dimension in dimensions:
        claim = by_dimension.get(dimension)
        if claim is not None:
            return claim
    return None


def build_comparison_matrix(session: Session) -> dict:
    components_cfg = _load_components()
    competitors = session.execute(
        select(Entity).where(Entity.kind == "competitor").order_by(Entity.slug)
    ).scalars().all()

    competitor_refs = [{"slug": entity.slug, "name": entity.name} for entity in competitors]

    components: list[dict] = []
    for component in components_cfg:
        key = component["key"]
        name = component["name"]
        dimensions = list(component["dimensions"])
        primary_dimension = dimensions[0]
        jfrog_position = _jfrog_position_for_dimension(primary_dimension)

        cells: list[dict] = []
        for competitor in competitors:
            claim = _claim_for_component(session, competitor.id, dimensions)
            if claim is None:
                cells.append(
                    {
                        "competitor": competitor.slug,
                        "competitor_name": competitor.name,
                        "stance": "no_claim",
                        "summary": _NO_CLAIM_SUMMARY,
                        "jfrog_position": jfrog_position,
                        "evidence": [],
                    }
                )
            else:
                cells.append(
                    {
                        "competitor": competitor.slug,
                        "competitor_name": competitor.name,
                        "stance": "comparable",
                        "summary": claim.claim_text or "",
                        "jfrog_position": jfrog_position,
                        "evidence": evidence_for_claim(session, claim),
                    }
                )

        components.append({"key": key, "name": name, "cells": cells})

    return {"components": components, "competitors": competitor_refs}
