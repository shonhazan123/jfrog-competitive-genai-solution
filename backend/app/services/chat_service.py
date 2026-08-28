from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent.graphs.chat.graph import build_chat_graph
from agent.llm import get_model, prompt as load_prompt
from agent.log import get_logger, step
from app.models.registry import Entity, Source
from app.serializers.common import fmt_ts
from app.services.citation import DeliveryRecord, build_citation, citation_to_dict
from app.services.config_overrides import current_config
from app.services.retrieval.query import search

logger = get_logger("app.chat_service")


class _ChatFilters(BaseModel):
    entity: str | None = None
    signal_type: str | None = None


class _ChatStep(BaseModel):
    tool: str
    query: str
    preset: str
    filters: _ChatFilters = Field(default_factory=_ChatFilters)
    reason: str = ""


class _ChatPlan(BaseModel):
    expanded_query: str
    steps: list[_ChatStep] = Field(default_factory=list)


class _ChatDraft(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)


def _build_plan_model():
    llm = get_model("chat_plan").with_structured_output(_ChatPlan, strict=True)

    class Adapter:
        def plan(self, message: str, transcript: str, presets: list[str],
                 filter_fields: list[str]) -> dict[str, Any]:
            payload = {"message": message, "transcript": transcript,
                       "presets": presets, "filter_fields": filter_fields}
            prompt_text = load_prompt("chat_plan") + "\n\nDATA:\n" + json.dumps(payload, default=str)
            step(logger, "chat.llm.plan", message=message)
            result = llm.invoke(prompt_text)
            return result.model_dump()

    return Adapter()


def _build_draft_model():
    llm = get_model("chat_draft").with_structured_output(_ChatDraft, strict=True)

    class Adapter:
        def draft(self, question: str, hits: list, persona: str | None,
                  transcript: str) -> dict[str, Any]:
            evidence = [{"id": str(h["id"]), "text": h["text"]} for h in hits]
            payload = {"question": question, "evidence": evidence,
                       "persona": persona, "transcript": transcript}
            prompt_text = load_prompt("chat_draft") + "\n\nDATA:\n" + json.dumps(payload, default=str)
            step(logger, "chat.llm.draft", question=question, evidence_chunks=len(evidence))
            result = llm.invoke(prompt_text)
            return {"answer": result.answer, "citations": result.citations}

    return Adapter()


def format_evidence(session: Session, hits: list[dict], citations: list[str]) -> list[dict]:
    sources = {source.id: source for source in session.query(Source).all()}
    cited = set(citations)
    evidence: list[dict] = []
    n = 1
    for hit in hits:
        hit_id = str(hit["id"])
        if hit_id not in cited:
            continue
        source = sources.get(hit.get("source_id"))
        fetched_at = source.last_checked_at if source and source.last_checked_at else datetime.now(UTC)
        record = DeliveryRecord(
            source_name=source.key.replace("_", " ").title() if source else "unknown",
            source_url=source.url if source else "",
            fetched_at=fetched_at,
            provenance="extracted",
            reliability_grade=hit.get("reliability_grade") or (source.reliability_grade if source else "C"),
        )
        evidence.append(
            {
                "n": n,
                "quote": hit["text"],
                "source_url": source.url if source else "",
                "source_name": source.key.replace("_", " ").title() if source else "unknown",
                "captured_at": fmt_ts(fetched_at),
                "reliability_grade": hit.get("reliability_grade") or (source.reliability_grade if source else "C"),
                "credibility_score": 2,
                "citation": citation_to_dict(build_citation(record)),
            }
        )
        n += 1
    return evidence


def _build_deps(session: Session):
    cfg = current_config()
    rcfg = cfg.retrieval

    class Deps:
        presets = list(rcfg.presets.keys())
        filter_fields = ["entity", "signal_type"]
        _plan_model = None
        _draft_model = None

        @property
        def plan_model(self):
            if self._plan_model is None:
                self._plan_model = _build_plan_model()
            return self._plan_model

        @property
        def draft_model(self):
            if self._draft_model is None:
                self._draft_model = _build_draft_model()
            return self._draft_model

        def resolve_entity(self, slug: str) -> list[int]:
            entity = session.query(Entity).filter_by(slug=slug).one_or_none()
            return [entity.id] if entity else []

        def retrieve(self, *, query: str, preset: str, filters: dict) -> list[dict]:
            hits = search(session, query=query, preset=preset, filters=filters, cfg=cfg)
            return [
                {
                    "id": str(hit.chunk_id),
                    "text": hit.text,
                    "source_id": hit.source_id,
                    "reliability_grade": hit.reliability_grade,
                }
                for hit in hits
            ]

        def format_sources(self, hits: list[dict], citations: list[str]) -> list[dict]:
            return format_evidence(session, hits, citations)

    return Deps()


def answer_chat(session: Session, message: str, history: list[dict] | None = None,
                persona: str | None = None, conversation_id: str | None = None) -> dict:
    """Bridge POST /chat to the chat graph without importing langgraph in app/."""
    step(logger, "chat.request.start", message=message, persona=persona,
         history=len(history or []))
    deps = _build_deps(session)
    graph = build_chat_graph(deps)
    try:
        result = graph.invoke({
            "message": message,
            "window": history or [],
            "persona": persona,
        })
    except Exception:
        logger.exception("chat.request.failed message=%r", message)
        raise
    grounded = bool(result.get("grounded"))
    step(logger, "chat.request.done", grounded=grounded,
         sources=len(result.get("sources", [])))
    return {
        "conversation_id": conversation_id,
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "grounded": grounded,
        "plan": result.get("plan", {}),
        "reason": result.get("reason") or None,
        "nearby_evidence": result.get("nearby_evidence", []),
    }
