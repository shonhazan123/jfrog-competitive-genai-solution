from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any, TypedDict
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent.graphs.chat.graph import (
    build_chat_graph,
    execute_steps,
    _is_grounded,
    _transcript,
    _valid_steps,
)
from agent.llm import get_embedder, get_model, prompt as load_prompt
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


class _ChatDraftDict(TypedDict):
    # TypedDict (not Pydantic) so with_structured_output streams partial JSON:
    # the JSON parser emits the growing `answer` as keys become available.
    answer: str
    citations: list[str]


def _draft_prompt(question: str, hits: list, persona: str | None, transcript: str) -> str:
    evidence = [{"id": str(h["id"]), "text": h["text"]} for h in hits]
    payload = {"question": question, "evidence": evidence,
               "persona": persona, "transcript": transcript}
    return load_prompt("chat_draft") + "\n\nDATA:\n" + json.dumps(payload, default=str)


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


def _build_embedder():
    """Query embedder for the semantic retrieval arm. Module-level so tests can
    monkeypatch it offline (the live embedder calls the OpenAI embeddings API)."""
    return get_embedder()


def _build_draft_model():
    llm = get_model("chat_draft").with_structured_output(_ChatDraft, strict=True)

    class Adapter:
        def draft(self, question: str, hits: list, persona: str | None,
                  transcript: str) -> dict[str, Any]:
            prompt_text = _draft_prompt(question, hits, persona, transcript)
            step(logger, "chat.llm.draft", question=question, evidence_chunks=len(hits))
            result = llm.invoke(prompt_text)
            return {"answer": result.answer, "citations": result.citations}

    return Adapter()


def _build_draft_stream_model():
    # TypedDict schema (no strict) so the JSON parser yields partial objects while
    # the model is still generating, letting us emit answer deltas as tokens.
    llm = get_model("chat_draft").with_structured_output(_ChatDraftDict)

    class Adapter:
        def stream(self, question: str, hits: list, persona: str | None,
                   transcript: str) -> Iterator[tuple[str, Any]]:
            prompt_text = _draft_prompt(question, hits, persona, transcript)
            step(logger, "chat.llm.draft.stream", question=question, evidence_chunks=len(hits))
            emitted = ""
            last: dict = {}
            for chunk in llm.stream(prompt_text):
                if not isinstance(chunk, dict):
                    continue
                last = chunk
                answer = chunk.get("answer") or ""
                # Emit only the newly appended suffix (guard against reorders).
                if isinstance(answer, str) and answer.startswith(emitted) and len(answer) > len(emitted):
                    yield ("token", answer[len(emitted):])
                    emitted = answer
            citations = last.get("citations") or []
            if not isinstance(citations, list):
                citations = []
            yield ("final", {"answer": emitted or (last.get("answer") or ""),
                             "citations": [str(c) for c in citations]})

    return Adapter()


def _domain(url: str) -> str:
    """Human-friendly source name from a URL (host, minus a leading www.)."""
    try:
        host = urlparse(url).netloc
    except ValueError:
        return url
    if host.startswith("www."):
        host = host[4:]
    return host or url


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
        # Prefer the chunk's own origin URL (where the finding was gathered) so
        # citations link to the live internet source, not an internal record.
        url = hit.get("url") or (source.url if source else "")
        if source is not None:
            source_name = source.key.replace("_", " ").title()
        elif url:
            source_name = _domain(url)
        else:
            source_name = "unknown"
        grade = hit.get("reliability_grade") or (source.reliability_grade if source else "C")
        fetched_at = source.last_checked_at if source and source.last_checked_at else datetime.now(UTC)
        record = DeliveryRecord(
            source_name=source_name,
            source_url=url,
            fetched_at=fetched_at,
            provenance="extracted",
            reliability_grade=grade,
        )
        evidence.append(
            {
                "n": n,
                "quote": hit["text"],
                "source_url": url,
                "source_name": source_name,
                "captured_at": fmt_ts(fetched_at),
                "reliability_grade": grade,
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
        _draft_stream_model = None
        _embedder = None

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

        @property
        def draft_stream_model(self):
            if self._draft_stream_model is None:
                self._draft_stream_model = _build_draft_stream_model()
            return self._draft_stream_model

        @property
        def embedder(self):
            if self._embedder is None:
                self._embedder = _build_embedder()
            return self._embedder

        def resolve_entity(self, slug: str) -> list[int]:
            entity = session.query(Entity).filter_by(slug=slug).one_or_none()
            return [entity.id] if entity else []

        def retrieve(self, *, query: str, preset: str, filters: dict) -> list[dict]:
            # Pass the embedder so retrieval runs the SEMANTIC (pgvector) arm as
            # well as lexical. Without it, natural-language planner queries (e.g.
            # "latest news about Sonatype") match zero chunks whose text lacks
            # those literal words, and every turn refuses. Chunks are embedded.
            hits = search(session, query=query, preset=preset, filters=filters,
                          cfg=cfg, embedder=self.embedder)
            return [
                {
                    "id": str(hit.chunk_id),
                    "text": hit.text,
                    "source_id": hit.source_id,
                    "url": hit.url,
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


_REFUSAL = "I don't have grounded evidence to answer that."


def answer_chat_stream(session: Session, message: str, history: list[dict] | None = None,
                       persona: str | None = None,
                       conversation_id: str | None = None) -> Iterator[dict]:
    """Streaming variant of answer_chat. Yields event dicts:
      {"type": "plan",  "expanded_query": str, "steps": int}
      {"type": "token", "text": str}                     # answer deltas
      {"type": "done",  "grounded": bool, "answer": str, "sources": [...],
                        "reason": str|None, "nearby_evidence": [...],
                        "conversation_id": str|None}

    Answer tokens stream before the grounding gate runs, so the terminal `done`
    event carries the authoritative grounded flag/sources. On a failed gate the
    client must discard the streamed provisional text and show the refusal.
    """
    step(logger, "chat.stream.start", message=message, persona=persona,
         history=len(history or []))
    window = history or []
    deps = _build_deps(session)
    transcript = _transcript(window)

    # 1) Plan
    step(logger, "chat.plan.start", message=message)
    raw_plan = deps.plan_model.plan(message, transcript, deps.presets, deps.filter_fields)
    steps = _valid_steps(raw_plan, deps.presets)
    expanded = raw_plan.get("expanded_query") or message
    step(logger, "chat.plan.done", steps=len(steps), expanded_query=expanded)
    yield {"type": "plan", "expanded_query": expanded, "steps": len(steps)}

    # 2) Execute (retrieve)
    hits = execute_steps(deps, steps)
    step(logger, "chat.execute.done", hits=len(hits))
    if not hits:
        step(logger, "chat.draft.refuse", reason="no_hits")
        yield {"type": "done", "grounded": False, "answer": _REFUSAL, "sources": [],
               "reason": "No grounded evidence to support an answer.",
               "nearby_evidence": [], "conversation_id": conversation_id}
        return

    # 3) Draft (stream answer tokens, then gate on citations)
    question = expanded or message
    answer = ""
    citations: list[str] = []
    for kind, payload in deps.draft_stream_model.stream(question, hits, persona, transcript):
        if kind == "token":
            answer += payload
            yield {"type": "token", "text": payload}
        elif kind == "final":
            answer = payload.get("answer") or answer
            citations = payload.get("citations") or []

    if _is_grounded(citations, hits):
        sources = deps.format_sources(hits, citations)
        step(logger, "chat.draft.done", citations=len(citations), sources=len(sources))
        yield {"type": "done", "grounded": True, "answer": answer, "sources": sources,
               "reason": None, "nearby_evidence": [], "conversation_id": conversation_id}
        return

    step(logger, "chat.draft.refuse", reason="citations_not_in_hits")
    cited = set(citations)
    nearby = [{"text": h["text"]} for h in hits if str(h["id"]) not in cited][:3]
    yield {"type": "done", "grounded": False, "answer": _REFUSAL, "sources": [],
           "reason": "Answer is not supported by grounded evidence.",
           "nearby_evidence": nearby, "conversation_id": conversation_id}
