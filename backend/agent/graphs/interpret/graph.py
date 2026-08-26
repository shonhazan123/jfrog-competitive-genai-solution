from langgraph.graph import END, START, StateGraph
from agent.graphs.interpret.state import InterpretState
from agent.nodes import contextualize, extract, quarantine, repair, sanitize, verify

def _after_verify(state: InterpretState) -> str:
    if state["verification"]["ok"]:
        return "crossref"
    if state.get("repair_attempts", 0) < state.get("_max_repairs", 2):
        return "repair"
    return "quarantine"

def build_interpret_graph(deps):
    builder = StateGraph(InterpretState)
    builder.add_node("sanitize", lambda s: sanitize.sanitize(s, deps))
    builder.add_node("extract", lambda s: extract.extract(s, deps))
    builder.add_node("verify", lambda s: verify.verify(s, deps))
    builder.add_node("repair", lambda s: repair.repair(s, deps))
    builder.add_node("quarantine", lambda s: quarantine.quarantine(s, deps))
    builder.add_node("crossref", lambda s: {"relations": deps.crossref(s),
                                            "trace": s.get("trace", []) + [{"node": "crossref"}]})
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
