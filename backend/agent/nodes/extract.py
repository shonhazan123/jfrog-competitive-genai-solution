from agent.log import get_logger, step

logger = get_logger("agent.extract")


def _as_dict(result) -> dict:
    if isinstance(result, dict):
        return result
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return dict(result)


def extract(state, deps):
    capture_id = state.get("capture_id")
    step(
        logger,
        "extract.start",
        capture_id=capture_id,
        chars=len(state["sanitized_text"]),
    )
    prompt_text = deps.prompt("extract").format(content=state["sanitized_text"])
    try:
        extraction = _as_dict(deps.extract_model.invoke(prompt_text))
    except Exception:
        logger.exception("extract.failed capture_id=%s", capture_id)
        raise
    claims = extraction.get("claims", [])
    step(
        logger,
        "extract.done",
        capture_id=capture_id,
        claims=len(claims),
        signal_type=extraction.get("signal_type"),
        headline=extraction.get("headline"),
    )
    return {
        "extraction": extraction,
        "trace": state.get("trace", []) + [{"node": "extract"}],
    }
