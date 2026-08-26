def verify(state, deps):
    extraction = state.get("extraction") or {}
    claims = extraction.get("claims", [])
    verified_claims = []
    failures = []
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
    updated_extraction = {**extraction, "claims": verified_claims if claims else []}
    return {
        "verification": {"ok": ok, "verified_claims": verified_claims, "failures": failures},
        "extraction": updated_extraction,
        "trace": state.get("trace", []) + [{"node": "verify", "ok": ok}],
    }
