def _as_dict(result) -> dict:
    if isinstance(result, dict):
        return result
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return dict(result)

def repair(state, deps):
    attempts = state.get("repair_attempts", 0) + 1
    failures = state.get("verification", {}).get("failures", [])
    feedback = f"Verification failed for claims: {failures}. Return only verifiable quotes."
    prompt_text = deps.prompt("extract").format(content=state["sanitized_text"])
    extraction = _as_dict(deps.extract_model.invoke(f"{feedback}\n{prompt_text}"))
    return {
        "repair_attempts": attempts,
        "extraction": extraction,
        "trace": state.get("trace", []) + [{"node": "repair", "attempt": attempts}],
    }
