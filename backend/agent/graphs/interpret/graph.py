from langgraph.graph import END, START, StateGraph
from agent.graphs.interpret.state import InterpretState
from agent.log import get_logger, step
from agent.nodes import contextualize, extract, quarantine, repair, sanitize, verify

logger = get_logger("agent.interpret")


def _after_verify(state: InterpretState) -> str:
    next_step = "crossref"
    if not state["verification"]["ok"]:
        if state.get("repair_attempts", 0) < state.get("_max_repairs", 2):
            next_step = "repair"
        else:
            next_step = "quarantine"
    step(
        logger,
        "interpret.route",
        capture_id=state.get("capture_id"),
        from_node="verify",
        to_node=next_step,
        verification_ok=state["verification"]["ok"],
        repair_attempts=state.get("repair_attempts", 0),
    )
    return next_step


def build_interpret_graph(deps):
    def _crossref(s):
        step(logger, "crossref.start", capture_id=s.get("capture_id"))
        relations = deps.crossref(s)
        step(logger, "crossref.done", capture_id=s.get("capture_id"), relations=len(relations))
        return {
            "relations": relations,
            "trace": s.get("trace", []) + [{"node": "crossref"}],
        }

    builder = StateGraph(InterpretState)
    builder.add_node("sanitize", lambda s: sanitize.sanitize(s, deps))
    builder.add_node("extract", lambda s: extract.extract(s, deps))
    builder.add_node("verify", lambda s: verify.verify(s, deps))
    builder.add_node("repair", lambda s: repair.repair(s, deps))
    builder.add_node("quarantine", lambda s: quarantine.quarantine(s, deps))
    builder.add_node("crossref", _crossref)
    builder.add_node("contextualize", lambda s: contextualize.contextualize(s, deps))

    builder.add_edge(START, "sanitize")
    builder.add_edge("sanitize", "extract")
    builder.add_edge("extract", "verify")
    builder.add_conditional_edges("verify", _after_verify,
                                  {"crossref": "crossref", "repair": "repair",
                                   "quarantine": "quarantine"})
    builder.add_edge("repair", "verify")
    builder.add_edge("crossref", "contextualize")
    builder.add_edge("contextualize", END)
    builder.add_edge("quarantine", END)

    return builder.compile(checkpointer=deps.checkpointer)
