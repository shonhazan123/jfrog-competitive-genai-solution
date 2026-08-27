def test_industry_buckets_load_with_include_and_exclude():
    from app.services.research.industry_agent import load_buckets

    buckets = load_buckets()
    keys = {b["key"] for b in buckets}
    assert keys == {"supply_chain_vulns", "ai_secops", "pipeline_devsecops", "regulation_compliance"}
    ai = next(b for b in buckets if b["key"] == "ai_secops")
    assert "quantization" in ai["exclude"]      # model-quality news is out
    assert "poisoned model" in ai["include"]     # AI supply-chain security is in
