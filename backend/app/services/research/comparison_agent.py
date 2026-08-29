from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.ledger import Claim, Evidence
from app.models.registry import Entity
from app.services.comparison_matrix import load_dimensions
from app.services.research.competitors import load_competitors
from app.services.research.provenance import index_finding, record_finding


def build_cells() -> list[dict]:
    cells: list[dict] = []
    for comp in load_competitors():
        for dim in load_dimensions():
            cells.append(
                {
                    "competitor": comp["slug"],
                    "name": comp["name"],
                    "aliases": comp.get("aliases") or [],
                    "dimension": dim["key"],
                    "label": dim["label"],
                    "probe_keywords": dim["probe_keywords"],
                    "jfrog_reference": dim["jfrog_position"],
                }
            )
    return cells


def _find_claim(session: Session, competitor_id: int, jfrog_id: int, dimension: str) -> Claim | None:
    return (
        session.query(Claim)
        .filter_by(
            asserting_entity_id=competitor_id,
            subject_entity_id=jfrog_id,
            dimension=dimension,
        )
        .one_or_none()
    )


def persist_comparison(session: Session, drafts: list[dict]) -> int:
    jfrog = session.query(Entity).filter_by(slug="jfrog").one()
    now = datetime.now(UTC)
    written = 0
    for draft in drafts:
        if draft.get("stance") == "none":
            continue
        competitor = session.query(Entity).filter_by(slug=draft["competitor"]).one()
        capture = record_finding(
            session,
            "comparison",
            draft["source_url"],
            draft["summary"],
        )
        claim = _find_claim(session, competitor.id, jfrog.id, draft["dimension"])
        if claim is None:
            claim = Claim(
                subject_entity_id=jfrog.id,
                asserting_entity_id=competitor.id,
                claim_text=draft["summary"],
                claim_type="positioning",
                capability_tags=[draft["dimension"]],
                dimension=draft["dimension"],
                stance=draft["stance"],
                reliability_grade="C",
                first_seen_at=now,
                last_confirmed_at=now,
            )
            session.add(claim)
        else:
            claim.claim_text = draft["summary"]
            claim.stance = draft["stance"]
            claim.last_confirmed_at = now
        session.flush()

        existing_evidence = (
            session.query(Evidence).filter_by(claim_id=claim.id).first()
        )
        if existing_evidence is None:
            session.add(
                Evidence(
                    claim_id=claim.id,
                    capture_id=capture.id,
                    quote=draft["summary"],
                    quote_offset=0,
                )
            )

        index_finding(
            session,
            record_type="claim",
            record_id=claim.id,
            text=draft["summary"],
            entity_id=competitor.id,
            signal_type="positioning_messaging",
            published_at=now,
            reliability_grade="C",
            url=capture.blob_path,
        )
        written += 1
    return written


def run_comparison(progress=None) -> dict:
    from agent.graphs.research.comparison.deps import CellVerdict, ComparisonDeps
    from agent.graphs.research.skeleton import run_research
    from agent.llm import get_model

    if progress is None:
        def progress(*_args, **_kwargs):
            return None

    gate = get_model("gate").with_structured_output(CellVerdict, strict=True)
    deps = ComparisonDeps(build_cells(), gate_model=gate)
    drafts = run_research(deps, progress=progress)
    progress("writing")
    with SessionLocal() as session:
        progress("saving")
        n = persist_comparison(session, drafts)
        session.commit()
    return {"comparison_items": n}
