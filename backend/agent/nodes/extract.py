def _as_dict(result) -> dict:
    if isinstance(result, dict):
        return result
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return dict(result)

def extract(state, deps):
    prompt_text = deps.prompt("extract").format(content=state["sanitized_text"])
    extraction = _as_dict(deps.extract_model.invoke(prompt_text))
    return {
        "extraction": extraction,
        "trace": state.get("trace", []) + [{"node": "extract"}],
    }
