from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.graphs.ask.state import AskState


def _hit_id(hit) -> str:
    if isinstance(hit, dict):
        return hit["id"]
    return hit.id


def _is_grounded(result: dict, hits: list) -> bool:
    citations = result.get("citations", [])
    if not citations:
        return False
    hit_ids = {_hit_id(h) for h in hits}
    return all(citation in hit_ids for citation in citations)


def classify_intent(state: AskState, deps) -> dict:
    question = state["question"].lower()
    filters: dict = {}
    if "sonatype" in question:
        filters["entity"] = "sonatype"
    elif "jfrog" in question:
        filters["entity"] = "jfrog"
    # Raw hit objects live on deps, never in the checkpointed state — the
    # MemorySaver serializes state with msgpack, which cannot encode arbitrary
    # retrieval objects. deps is already mutated for tool_calls, so this is the
    # established place for per-invocation scratch that must not be serialized.
    deps.accumulated_hits = []
    return {
        "filters": filters,
        "tool_iterations": 0,
        "answer": "",
        "citations": [],
        "refused": False,
        "reason": "",
    }


def tool_loop(state: AskState, deps) -> dict:
    new_hits = deps.retrieve(state["question"], state.get("filters", {}))
    deps.tool_calls += 1
    existing = list(getattr(deps, "accumulated_hits", []))
    seen = {_hit_id(h) for h in existing}
    for hit in new_hits:
        hit_id = _hit_id(hit)
        if hit_id not in seen:
            seen.add(hit_id)
            existing.append(hit)
    deps.accumulated_hits = existing
    return {
        "tool_iterations": state.get("tool_iterations", 0) + 1,
    }


def grounding_gate(state: AskState, deps) -> dict:
    hits = list(getattr(deps, "accumulated_hits", []))
    if not hits:
        return {
            "refused": True,
            "reason": "No grounded evidence to support an answer.",
            "citations": [],
            "answer": "",
        }
    result = deps.model.answer(state["question"], hits)
    if _is_grounded(result, hits):
        return {
            "answer": result["answer"],
            "citations": result["citations"],
            "refused": False,
            "reason": "",
        }
    return {
        "refused": True,
        "reason": "Answer is not supported by grounded evidence.",
        "citations": [],
        "answer": "",
    }


def answer(state: AskState, deps) -> dict:
    return {"refused": False}


def refuse(state: AskState, deps) -> dict:
    reason = state.get("reason", "")
    if "grounded evidence" not in reason.lower():
        reason = "No grounded evidence to support an answer."
    return {
        "refused": True,
        "citations": [],
        "reason": reason,
        "answer": "",
    }


def _after_grounding(state: AskState) -> str:
    # Route on the real, schema-declared `refused` field. A transient key like
    # `_route` would be stripped by LangGraph (not in AskState) and always
    # default to refuse.
    return "refuse" if state.get("refused") else "answer"


def build_ask_graph(deps):
    def _should_continue(state: AskState) -> str:
        if deps.always_call_tools and state.get("tool_iterations", 0) < deps.max_tool_calls:
            return "tool_loop"
        return "grounding_gate"

    builder = StateGraph(AskState)
    builder.add_node("classify_intent", lambda s: classify_intent(s, deps))
    builder.add_node("tool_loop", lambda s: tool_loop(s, deps))
    builder.add_node("grounding_gate", lambda s: grounding_gate(s, deps))
    builder.add_node("answer", lambda s: answer(s, deps))
    builder.add_node("refuse", lambda s: refuse(s, deps))

    builder.add_edge(START, "classify_intent")
    builder.add_edge("classify_intent", "tool_loop")
    builder.add_conditional_edges(
        "tool_loop",
        _should_continue,
        {"tool_loop": "tool_loop", "grounding_gate": "grounding_gate"},
    )
    builder.add_conditional_edges(
        "grounding_gate",
        _after_grounding,
        {"answer": "answer", "refuse": "refuse"},
    )
    builder.add_edge("answer", END)
    builder.add_edge("refuse", END)

    checkpointer = getattr(deps, "checkpointer", None) or MemorySaver()
    return builder.compile(checkpointer=checkpointer)
