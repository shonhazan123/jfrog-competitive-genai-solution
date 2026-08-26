def _as_dict(result) -> dict:
    if isinstance(result, dict):
        return result
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return dict(result)

def contextualize(state, deps):
    contextualization = _as_dict(deps.contextualize_model.invoke(state))
    return {
        "contextualization": contextualization,
        "status": "ok",
        "trace": state.get("trace", []) + [{"node": "contextualize"}],
    }
