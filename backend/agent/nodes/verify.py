from agent.log import get_logger, step

logger = get_logger("agent.verify")


def verify(state, deps):
    capture_id = state.get("capture_id")
    extraction = state.get("extraction") or {}
    claims = extraction.get("claims", [])
    verified_claims = []
    failures = []
    step(logger, "verify.start", capture_id=capture_id, claims=len(claims))
    for index, claim in enumerate(claims):
        match = deps.verify_quote(claim["quote"], state["sanitized_text"], deps.verification_config)
        if match.ok:
            verified_claims.append({
                **claim,
                "quote": match.quote,
                "offset": match.offset,
                "method": match.method,
            })
        else:
            failures.append({"index": index, "claim": claim})

    ok = len(failures) == 0
    if ok:
        step(logger, "verify.done", capture_id=capture_id, verified=len(verified_claims))
    else:
        step(
            logger,
            "verify.failed",
            capture_id=capture_id,
            verified=len(verified_claims),
            failures=len(failures),
            failed_quotes=[failure["claim"].get("quote") for failure in failures[:3]],
        )
    updated_extraction = {**extraction, "claims": verified_claims if claims else []}
    return {
        "verification": {"ok": ok, "verified_claims": verified_claims, "failures": failures},
        "extraction": updated_extraction,
        "trace": state.get("trace", []) + [{"node": "verify", "ok": ok}],
    }
