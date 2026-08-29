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
from app.services.research.provenance import index_finding, record_finding
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
    written = 0
    for draft in drafts:
        for item in draft["items"]:
            capture = record_finding(
                session,
                "industry",
                item["source_url"],
                f'{item["headline"]}\n{item["body"]}',
            )
            facets = {
                "signal_type": draft["signal_type"],
                "subject_entity": None,
                "asserting_entity": "industry",
                "entity_tier": industry.tier,
                "reliability_grade": "C",
                "corroboration_count": 1,
                "capability_tags": [],
                "occurred_at": now,
                "text": item["body"],
            }
            signal = Signal(
                source_id=capture.source_id,
                entity_id=industry.id,
                signal_type=draft["signal_type"],
                theme_key=draft["bucket"],
                headline=item["headline"][:256],
                occurred_at=now,
                cluster_key=hashlib.sha256(
                    (draft["bucket"] + item["headline"]).encode()
                ).hexdigest()[:128],
                so_what_product=item["body"],
                why_it_matters=item["why_it_matters"],
                score_sales=score(facets, "sales", cfg).total,
                score_product=score(facets, "product", cfg).total,
                score_exec=score(facets, "exec", cfg).total,
            )
            session.add(signal)
            session.flush()
            session.add(
                SignalEvidence(
                    signal_id=signal.id,
                    capture_id=capture.id,
                    quote=item["headline"],
                    quote_offset=0,
                    match_method="synthesis",
                )
            )
            index_finding(
                session,
                record_type="signal",
                record_id=signal.id,
                text=item["body"],
                entity_id=industry.id,
                signal_type=draft["signal_type"],
                published_at=now,
                reliability_grade="C",
                url=capture.blob_path,
            )
            written += 1
    return written


def run_industry() -> dict:
    from agent.graphs.research.industry.deps import IndustryAssessment, IndustryDeps
    from agent.graphs.research.skeleton import run_research
    from agent.llm import get_model

    gate = get_model("gate").with_structured_output(IndustryAssessment, strict=True)
    deps = IndustryDeps(load_buckets(), gate_model=gate)
    drafts = run_research(deps)
    with SessionLocal() as session:
        n = persist_industry(session, drafts)
        session.commit()
    return {"industry_items": n}
