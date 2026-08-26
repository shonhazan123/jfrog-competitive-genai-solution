from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent.graphs.ask.graph import build_ask_graph
from agent.llm import get_checkpointer, prompt as load_prompt
from app.models.registry import Entity, Source
from app.serializers.common import fmt_ts
from app.services.config_overrides import current_config
from app.services.retrieval.query import search


class _AskAnswer(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)


def _lazy_model():
    from agent.llm import get_model

    llm = get_model("contextualize").with_structured_output(_AskAnswer, strict=True)

    class Adapter:
        def answer(self, question: str, hits: list) -> dict[str, Any]:
            evidence = []
            for hit in hits:
                hit_id = hit["id"] if isinstance(hit, dict) else hit.id
                text = hit["text"] if isinstance(hit, dict) else hit.text
                evidence.append({"id": str(hit_id), "text": text})
            prompt_text = (
                load_prompt("ask")
                + "\n\nDATA:\n"
                + json.dumps({"question": question, "evidence": evidence}, default=str)
            )
            result = llm.invoke(prompt_text)
            return {"answer": result.answer, "citations": result.citations}

    return Adapter()


def _build_deps(session: Session):
    cfg = current_config()

    class Deps:
        tool_calls = 0
        max_tool_calls = 4
        always_call_tools = True
        checkpointer = get_checkpointer()
        _model = None

        @property
        def model(self):
            if self._model is None:
                self._model = _lazy_model()
            return self._model

        def retrieve(self, question: str, filters: dict) -> list[dict]:
            entity_ids: list[int] = []
            if filters.get("entity"):
                entity = session.query(Entity).filter_by(slug=filters["entity"]).one_or_none()
                if entity:
                    entity_ids = [entity.id]
            hits = search(
                session,
                query=question,
                preset="ask_ledger",
                filters={"entity_ids": entity_ids} if entity_ids else {},
                cfg=cfg,
            )
            return [
                {
                    "id": str(hit.chunk_id),
                    "text": hit.text,
                    "source_id": hit.source_id,
                    "reliability_grade": hit.reliability_grade,
                }
                for hit in hits
            ]

    return Deps()


def _format_evidence(session: Session, hits: list[dict], citations: list[str]) -> list[dict]:
    sources = {source.id: source for source in session.query(Source).all()}
    cited = set(citations)
    evidence: list[dict] = []
    n = 1
    for hit in hits:
        hit_id = str(hit["id"])
        if hit_id not in cited:
            continue
        source = sources.get(hit.get("source_id"))
        evidence.append(
            {
                "n": n,
                "quote": hit["text"],
                "source_url": source.url if source else "",
                "source_name": source.key.replace("_", " ").title() if source else "unknown",
                "captured_at": fmt_ts(source.last_checked_at) if source else None,
                "reliability_grade": hit.get("reliability_grade") or (source.reliability_grade if source else "C"),
                "credibility_score": 2,
            }
        )
        n += 1
    return evidence


def answer_question(session: Session, question: str, persona: str | None = None) -> dict:
    """Bridge POST /ask to the agent graph without importing langgraph in app/."""
    deps = _build_deps(session)
    graph = build_ask_graph(deps)
    result = graph.invoke(
        {"question": question},
        config={"configurable": {"thread_id": f"ask:{hash(question) & 0xffff}"}},
    )
    refused = bool(result.get("refused"))
    hits = list(getattr(deps, "accumulated_hits", []))
    hit_dicts = [
        {
            "id": h["id"] if isinstance(h, dict) else h.id,
            "text": h["text"] if isinstance(h, dict) else h.text,
            "source_id": h.get("source_id") if isinstance(h, dict) else None,
            "reliability_grade": h.get("reliability_grade") if isinstance(h, dict) else None,
        }
        for h in hits
    ]
    citations = result.get("citations", [])
    evidence = _format_evidence(session, hit_dicts, citations) if not refused else []
    nearby: list[dict] = []
    if refused and hit_dicts:
        nearby = [{"text": h["text"]} for h in hit_dicts[:3]]
    return {
        "question": question,
        "persona": persona,
        "grounded": not refused,
        "answer": result.get("answer") or (result.get("reason") or ""),
        "evidence": evidence,
        "refusal_reason": result.get("reason") if refused else None,
        "nearby_evidence": nearby,
    }
