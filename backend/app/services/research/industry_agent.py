from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.db.session import SessionLocal
from app.models.registry import Entity
from app.models.signal import Signal, SignalEvidence
from app.services.research.dedup import dedupe_items
from app.services.research.provenance import index_finding, record_finding, sanitize_text
from app.services.scoring.materiality import score
from app.settings import settings


def load_buckets() -> list[dict]:
    data = yaml.safe_load(
        (Path(settings.config_dir) / "industry_buckets.yaml").read_text(encoding="utf-8")
    )
    return data["buckets"]


def persist_industry(session: Session, drafts: list[dict]) -> int:
    industry = session.query(Entity).filter_by(slug="industry").one()
    cfg = load_config()
    now = datetime.now(UTC)

    # Pass 1 — record every finding's capture and build a clusterable item.
    items: list[dict] = []
    for draft in drafts:
        for item in draft["items"]:
            headline = sanitize_text(item["headline"])
            body = sanitize_text(item["body"])
            why_it_matters = sanitize_text(item["why_it_matters"])
            capture = record_finding(
                session,
                "industry",
                item["source_url"],
                f"{headline}\n{body}",
            )
            items.append({
                "entity_slug": "industry",
                "signal_type": draft["signal_type"],
                "theme_key": draft["bucket"],
                "headline": headline,
                "body": body,
                "why_it_matters": why_it_matters,
                "capture": capture,
                "occurred_at": now,
            })

    # Pass 2 — one Signal per event; N framings become N evidence rows.
    written = 0
    for group in dedupe_items(items, cfg.materiality.cluster):
        rep = group[0]
        headline = rep["headline"]
        corroboration = len(group)
        facets = {
            "signal_type": rep["signal_type"],
            "subject_entity": None,
            "asserting_entity": "industry",
            "entity_tier": industry.tier,
            "reliability_grade": "C",
            "corroboration_count": corroboration,
            "capability_tags": [],
            "occurred_at": now,
            "text": rep["body"],
        }
        signal = Signal(
            source_id=rep["capture"].source_id,
            entity_id=industry.id,
            signal_type=rep["signal_type"],
            theme_key=rep["theme_key"],
            headline=headline[:256],
            occurred_at=now,
            cluster_key=hashlib.sha256(
                (rep["theme_key"] + headline).encode()
            ).hexdigest()[:128],
            corroboration_count=corroboration,
            so_what_product=rep["body"],
            why_it_matters=rep["why_it_matters"],
            score_sales=score(facets, "sales", cfg).total,
            score_product=score(facets, "product", cfg).total,
            score_exec=score(facets, "exec", cfg).total,
        )
        session.add(signal)
        session.flush()
        for member in group:
            session.add(
                SignalEvidence(
                    signal_id=signal.id,
                    capture_id=member["capture"].id,
                    quote=member["headline"],
                    quote_offset=0,
                    match_method="synthesis",
                )
            )
        index_finding(
            session,
            record_type="signal",
            record_id=signal.id,
            text=rep["body"],
            entity_id=industry.id,
            signal_type=rep["signal_type"],
            published_at=now,
            reliability_grade="C",
            url=rep["capture"].blob_path,
        )
        written += 1
    return written


def run_industry(progress=None) -> dict:
    from agent.graphs.research.industry.deps import IndustryAssessment, IndustryDeps
    from agent.graphs.research.skeleton import run_research
    from agent.llm import get_model

    if progress is None:
        def progress(*_args, **_kwargs):
            return None

    gate = get_model("gate").with_structured_output(IndustryAssessment, strict=True)
    deps = IndustryDeps(load_buckets(), gate_model=gate)
    drafts = run_research(deps, progress=progress)
    progress("writing")
    with SessionLocal() as session:
        progress("saving")
        n = persist_industry(session, drafts)
        session.commit()
    return {"industry_items": n}
