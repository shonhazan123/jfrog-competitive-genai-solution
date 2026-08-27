from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from agent.graphs.interpret.graph import build_interpret_graph
from agent.llm import get_checkpointer, get_model, prompt as load_prompt
from agent.log import get_logger, step
from agent.schemas import Contextualisation, build_extraction_model
from app.config.loader import load_config
from app.models.capture import RawCapture
from app.models.registry import Entity, Source
from app.models.signal import AnalystQueue, Signal, SignalEvidence
from app.services.claim_lookup import DbClaimLookup
from app.services.scoring.materiality import score
from app.services.signals.clustering import cluster_key
from app.services.verification import verify_quote

PROMPT_VERSION = 1
logger = get_logger("app.agent_service")

@dataclass
class InterpretResult:
    status: str
    signal_id: int | None = None
    thread_id: str | None = None

def thread_id_for(capture_id: int, prompt_version: int = PROMPT_VERSION) -> str:
    return f"interpret:{capture_id}:v{prompt_version}"

def _persist_cluster_key(facets: dict, window_days: int) -> str:
    entity, tags, bucket = cluster_key(facets, window_days)
    payload = json.dumps([entity, sorted(tags), bucket], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()

def _entity_id(session: Session, slug: str | None) -> int | None:
    if not slug:
        return None
    entity = session.query(Entity).filter_by(slug=slug).one_or_none()
    return entity.id if entity else None

def _persist_signal(session: Session, capture: RawCapture, source: Source, final: dict) -> Signal:
    config = load_config()
    extraction = final.get("extraction") or {}
    contextualization = final.get("contextualization") or {}
    asserting_slug = extraction.get("asserting_entity")
    subject_slug = extraction.get("subject_entity")
    entity = session.query(Entity).filter_by(id=source.entity_id).one()
    occurred_at = extraction.get("occurred_at")
    if occurred_at and not isinstance(occurred_at, datetime):
        occurred_at = datetime.combine(occurred_at, datetime.min.time(), tzinfo=UTC)
    if not occurred_at:
        occurred_at = capture.fetched_at

    capability_tags: list[str] = []
    for claim in extraction.get("claims", []):
        capability_tags.extend(claim.get("capability_tags", []))
    capability_tags = list(dict.fromkeys(capability_tags))

    facets = {
        "signal_type": extraction.get("signal_type", "product_capability"),
        "subject_entity": subject_slug,
        "asserting_entity": asserting_slug,
        "entity_tier": entity.tier,
        "reliability_grade": source.reliability_grade,
        "corroboration_count": 1,
        "capability_tags": capability_tags,
        "occurred_at": occurred_at,
        "text": capture.extracted_text,
    }
    breakdown = {
        persona: score(facets, persona, config).parts
        for persona in ("sales", "product", "exec")
    }
    signal = Signal(
        source_id=source.id,
        entity_id=source.entity_id,
        subject_entity_id=_entity_id(session, subject_slug),
        signal_type=extraction.get("signal_type", "product_capability"),
        headline=extraction.get("headline", "")[:256],
        occurred_at=occurred_at,
        capability_tags=capability_tags,
        cluster_key=_persist_cluster_key({
            "entity": asserting_slug or entity.slug,
            "capability_tags": capability_tags,
            "occurred_at": occurred_at,
        }, config.materiality.cluster.window_days),
        score_sales=score(facets, "sales", config).total,
        score_product=score(facets, "product", config).total,
        score_exec=score(facets, "exec", config).total,
        score_breakdown={k: [list(p) for p in v] for k, v in breakdown.items()},
        so_what_sales=contextualization.get("so_what_sales"),
        so_what_product=contextualization.get("so_what_product"),
        so_what_exec=contextualization.get("so_what_exec"),
        why_it_matters=contextualization.get("why_it_matters"),
    )
    session.add(signal)
    session.flush()

    for claim in extraction.get("claims", []):
        offset = claim.get("offset", 0) or 0
        session.add(SignalEvidence(
            signal_id=signal.id,
            capture_id=capture.id,
            quote=claim["quote"],
            quote_offset=offset,
            match_method=claim.get("method", "exact"),
        ))
    session.flush()
    return signal

def _production_deps(session: Session):
    config = load_config()
    entities = [entity.slug for entity in config.entities]
    tags = config.signal_types.capability_tags
    extraction_model = build_extraction_model(entities, tags)
    extract_llm = get_model("extract").with_structured_output(extraction_model, strict=True)
    contextualize_llm = get_model("contextualize").with_structured_output(
        Contextualisation, strict=True,
    )
    claim_lookup = DbClaimLookup(session)

    class ContextualizeAdapter:
        def invoke(self, state):
            capture_id = state.get("capture_id")
            extraction = state.get("extraction") or {}
            verification = state.get("verification") or {}
            verified = verification.get("verified_claims") or extraction.get("claims") or []
            capability_tags: list[str] = []
            for claim in verified:
                capability_tags.extend(claim.get("capability_tags", []))
            payload = {
                "extraction": extraction,
                "verified_quotes": [claim.get("quote") for claim in verified],
                "relations": state.get("relations") or [],
                "jfrog_positions": {
                    tag: claim_lookup.jfrog_position(tag)
                    for tag in dict.fromkeys(capability_tags)
                },
            }
            step(
                logger,
                "interpret.contextualize.payload",
                capture_id=capture_id,
                verified_claims=len(verified),
                capability_tags=len(capability_tags),
            )
            prompt_text = (
                load_prompt("contextualize")
                + "\n\nDATA:\n"
                + json.dumps(payload, default=str)
            )
            return contextualize_llm.invoke(prompt_text)

    class RuntimeDeps:
        max_input_chars = 50_000
        max_repairs = 2
        verification_config = config.verification
        verify_quote = staticmethod(verify_quote)
        checkpointer = get_checkpointer()
        use_interrupt = True
        extract_model = extract_llm
        contextualize_model = ContextualizeAdapter()
        prompt = staticmethod(load_prompt)

        @staticmethod
        def crossref(_state):
            return []

    return RuntimeDeps()

def interpret_capture(capture_id: int, *, session: Session, deps=None) -> InterpretResult:
    capture = session.query(RawCapture).filter_by(id=capture_id).one()
    source = session.query(Source).filter_by(id=capture.source_id).one()
    if deps is None:
        deps = _production_deps(session)

    thread_id = thread_id_for(capture_id)
    step(
        logger,
        "interpret.capture.start",
        capture_id=capture_id,
        source_key=source.key,
        thread_id=thread_id,
        text_chars=len(capture.extracted_text or ""),
    )
    graph = build_interpret_graph(deps)
    try:
        final = graph.invoke(
            {
                "capture_id": capture_id,
                "raw_text": capture.extracted_text,
                "source_meta": {"source_key": source.key, "entity_id": source.entity_id},
                "repair_attempts": 0,
                "_max_repairs": deps.max_repairs,
            },
            config={"configurable": {"thread_id": thread_id}},
        )
    except Exception:
        logger.exception(
            "interpret.capture.failed capture_id=%s thread_id=%s",
            capture_id,
            thread_id,
        )
        raise

    status = final.get("status", "ok")
    if status == "quarantined":
        failures = final.get("verification", {}).get("failures", [])
        step(
            logger,
            "interpret.capture.quarantined",
            capture_id=capture_id,
            thread_id=thread_id,
            failures=len(failures),
        )
        session.add(AnalystQueue(
            thread_id=thread_id,
            capture_id=capture_id,
            reason="verification_failed",
            payload={
                "extraction": final.get("extraction"),
                "failures": failures,
            },
        ))
        session.flush()
        return InterpretResult(status="quarantined", thread_id=thread_id)

    signal = _persist_signal(session, capture, source, final)
    step(
        logger,
        "interpret.capture.done",
        capture_id=capture_id,
        thread_id=thread_id,
        signal_id=signal.id,
        headline=signal.headline,
    )
    return InterpretResult(status="ok", signal_id=signal.id, thread_id=thread_id)

def resume_queue_item(thread_id: str, decision: dict, *, session: Session, deps=None) -> InterpretResult:
    row = session.query(AnalystQueue).filter_by(thread_id=thread_id).one()
    if decision.get("action") == "reject":
        row.resolved_at = datetime.now(UTC)
        session.flush()
        return InterpretResult(status="rejected", thread_id=thread_id)
    return interpret_capture(row.capture_id, session=session, deps=deps)
