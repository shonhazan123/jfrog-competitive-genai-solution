from langgraph.graph import END, START, StateGraph

from agent.graphs.chat.state import ChatState
from agent.log import get_logger, step

logger = get_logger("agent.chat")

_REFUSAL = "I don't have grounded evidence to answer that."


def _hit_id(hit) -> str:
    return hit["id"] if isinstance(hit, dict) else hit.id


def _is_grounded(citations: list, hits: list) -> bool:
    if not citations:
        return False
    hit_ids = {_hit_id(h) for h in hits}
    return all(c in hit_ids for c in citations)


def _transcript(window: list[dict]) -> str:
    lines = []
    for turn in window or []:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _valid_steps(plan: dict, presets: list[str]) -> list[dict]:
    steps = []
    for s in plan.get("steps", []) or []:
        if s.get("tool") != "retrieve":
            continue
        if s.get("preset") not in presets:
            continue
        if not s.get("query"):
            continue
        steps.append(s)
    return steps


def plan_node(state: ChatState, deps) -> dict:
    message = state["message"]
    transcript = _transcript(state.get("window", []))
    step(logger, "chat.plan.start", message=message)
    raw = deps.plan_model.plan(message, transcript, deps.presets, deps.filter_fields)
    steps = _valid_steps(raw, deps.presets)
    expanded = raw.get("expanded_query") or message
    plan = {"expanded_query": expanded, "steps": steps}
    step(logger, "chat.plan.done", steps=len(steps), expanded_query=expanded)
    return {"plan": plan, "expanded_query": expanded}


def execute_node(state: ChatState, deps) -> dict:
    plan = state.get("plan", {})
    hits: list = []
    seen: set = set()
    for s in plan.get("steps", []):
        filters = s.get("filters") or {}
        entity_slug = filters.get("entity")
        retrieval_filters: dict = {}
        if entity_slug:
            entity_ids = deps.resolve_entity(entity_slug)
            if not entity_ids:
                step(logger, "chat.execute.skip", entity=entity_slug, reason="unresolved")
                continue
            retrieval_filters = {"entity_ids": entity_ids}
        new_hits = deps.retrieve(query=s["query"], preset=s["preset"], filters=retrieval_filters)
        for h in new_hits:
            hid = _hit_id(h)
            if hid not in seen:
                seen.add(hid)
                hits.append(h)
    step(logger, "chat.execute.done", hits=len(hits))
    return {"hits": hits}


def draft_node(state: ChatState, deps) -> dict:
    hits = state.get("hits", [])
    if not hits:
        step(logger, "chat.draft.refuse", reason="no_hits")
        return {
            "answer": _REFUSAL,
            "citations": [],
            "sources": [],
            "grounded": False,
            "reason": "No grounded evidence to support an answer.",
            "nearby_evidence": [],
        }
    question = state.get("expanded_query") or state["message"]
    transcript = _transcript(state.get("window", []))
    result = deps.draft_model.draft(question, hits, state.get("persona"), transcript)
    citations = result.get("citations", [])
    answer = result.get("answer", "")
    if _is_grounded(citations, hits):
        sources = deps.format_sources(hits, citations)
        step(logger, "chat.draft.done", citations=len(citations), sources=len(sources))
        return {
            "answer": answer,
            "citations": citations,
            "sources": sources,
            "grounded": True,
            "reason": "",
            "nearby_evidence": [],
        }
    step(logger, "chat.draft.refuse", reason="citations_not_in_hits")
    cited = set(citations)
    nearby = [{"text": h["text"]} for h in hits if _hit_id(h) not in cited][:3]
    return {
        "answer": _REFUSAL,
        "citations": [],
        "sources": [],
        "grounded": False,
        "reason": "Answer is not supported by grounded evidence.",
        "nearby_evidence": nearby,
    }


def build_chat_graph(deps):
    builder = StateGraph(ChatState)
    builder.add_node("plan", lambda s: plan_node(s, deps))
    builder.add_node("execute", lambda s: execute_node(s, deps))
    builder.add_node("draft", lambda s: draft_node(s, deps))
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "execute")
    builder.add_edge("execute", "draft")
    builder.add_edge("draft", END)
    return builder.compile()
