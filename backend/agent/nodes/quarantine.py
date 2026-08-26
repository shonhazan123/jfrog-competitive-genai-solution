def quarantine(state, deps):
    payload = {
        "capture_id": state["capture_id"],
        "extraction": state.get("extraction"),
        "failures": state.get("verification", {}).get("failures", []),
    }
    update = {
        "status": "quarantined",
        "trace": state.get("trace", []) + [{"node": "quarantine"}],
    }
    if getattr(deps, "use_interrupt", True):
        from langgraph.types import interrupt
        interrupt(payload)
    return update
