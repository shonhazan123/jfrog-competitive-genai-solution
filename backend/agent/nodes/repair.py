from agent.log import get_logger, step

logger = get_logger("agent.repair")


def _as_dict(result) -> dict:
    if isinstance(result, dict):
        return result
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return dict(result)


def repair(state, deps):
    capture_id = state.get("capture_id")
    attempts = state.get("repair_attempts", 0) + 1
    failures = state.get("verification", {}).get("failures", [])
    step(
        logger,
        "repair.start",
        capture_id=capture_id,
        attempt=attempts,
        failures=len(failures),
    )
    feedback = f"Verification failed for claims: {failures}. Return only verifiable quotes."
    prompt_text = deps.prompt("extract").format(content=state["sanitized_text"])
    try:
        extraction = _as_dict(deps.extract_model.invoke(f"{feedback}\n{prompt_text}"))
    except Exception:
        logger.exception("repair.failed capture_id=%s attempt=%s", capture_id, attempts)
        raise
    step(
        logger,
        "repair.done",
        capture_id=capture_id,
        attempt=attempts,
        claims=len(extraction.get("claims", [])),
    )
    return {
        "repair_attempts": attempts,
        "extraction": extraction,
        "trace": state.get("trace", []) + [{"node": "repair", "attempt": attempts}],
    }
