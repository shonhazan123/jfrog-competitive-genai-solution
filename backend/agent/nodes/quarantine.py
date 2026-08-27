from agent.log import get_logger, step

logger = get_logger("agent.quarantine")


def quarantine(state, deps):
    capture_id = state.get("capture_id")
    failures = state.get("verification", {}).get("failures", [])
    step(
        logger,
        "quarantine",
        capture_id=capture_id,
        failures=len(failures),
        repair_attempts=state.get("repair_attempts", 0),
    )
    payload = {
        "capture_id": capture_id,
        "extraction": state.get("extraction"),
        "failures": failures,
    }
    update = {
        "status": "quarantined",
        "trace": state.get("trace", []) + [{"node": "quarantine"}],
    }
    if getattr(deps, "use_interrupt", True):
        from langgraph.types import interrupt
        interrupt(payload)
    return update
