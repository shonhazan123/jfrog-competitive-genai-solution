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
from app.services.research.competitors import load_competitors
from app.settings import settings

_NO_CLAIM_SUMMARY = "No public claim on record."


def load_dimensions() -> list[dict]:
    data = yaml.safe_load(
        (Path(settings.config_dir) / "comparison_dimensions.yaml").read_text(encoding="utf-8")
    )
    return data["dimensions"]


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


def build_comparison_matrix(session: Session) -> dict:
    jfrog = session.execute(select(Entity).filter_by(slug="jfrog")).scalar_one_or_none()
    competitors_cfg = load_competitors()
    competitor_refs = [{"slug": c["slug"], "name": c["name"]} for c in competitors_cfg]

    dimensions_out: list[dict] = []
    for dim in load_dimensions():
        cells: list[dict] = []
        for comp in competitors_cfg:
            competitor = session.execute(
                select(Entity).filter_by(slug=comp["slug"])
            ).scalar_one_or_none()
            if competitor is None or jfrog is None:
                cells.append(
                    {
                        "competitor": comp["slug"],
                        "competitor_name": comp["name"],
                        "stance": "none",
                        "summary": _NO_CLAIM_SUMMARY,
                        "jfrog_position": dim["jfrog_position"],
                        "evidence": [],
                    }
                )
                continue

            claim = session.execute(
                select(Claim).where(
                    Claim.asserting_entity_id == competitor.id,
                    Claim.subject_entity_id == jfrog.id,
                    Claim.dimension == dim["key"],
                )
            ).scalar_one_or_none()

            if claim is None:
                cells.append(
                    {
                        "competitor": comp["slug"],
                        "competitor_name": comp["name"],
                        "stance": "none",
                        "summary": _NO_CLAIM_SUMMARY,
                        "jfrog_position": dim["jfrog_position"],
                        "evidence": [],
                    }
                )
            else:
                cells.append(
                    {
                        "competitor": comp["slug"],
                        "competitor_name": comp["name"],
                        "stance": claim.stance or "none",
                        "summary": claim.claim_text or "",
                        "jfrog_position": dim["jfrog_position"],
                        "evidence": evidence_for_claim(session, claim),
                    }
                )

        dimensions_out.append(
            {
                "key": dim["key"],
                "name": dim["label"],
                "cells": cells,
            }
        )

    return {"dimensions": dimensions_out, "competitors": competitor_refs}
