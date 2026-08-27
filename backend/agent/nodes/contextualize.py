from agent.log import get_logger, step

logger = get_logger("agent.contextualize")


def _as_dict(result) -> dict:
    if isinstance(result, dict):
        return result
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return dict(result)


def contextualize(state, deps):
    capture_id = state.get("capture_id")
    step(logger, "contextualize.start", capture_id=capture_id)
    try:
        contextualization = _as_dict(deps.contextualize_model.invoke(state))
    except Exception:
        logger.exception("contextualize.failed capture_id=%s", capture_id)
        raise
    step(
        logger,
        "contextualize.done",
        capture_id=capture_id,
        relevance_adjustment=contextualization.get("relevance_adjustment"),
    )
    return {
        "contextualization": contextualization,
        "status": "ok",
        "trace": state.get("trace", []) + [{"node": "contextualize"}],
    }
