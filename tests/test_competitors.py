def test_active_competitor_set():
    from app.services.research.competitors import load_competitors

    slugs = {c["slug"] for c in load_competitors()}
    assert slugs == {"github", "sonatype", "snyk", "aqua", "checkmarx"}
    aqua = next(c for c in load_competitors() if c["slug"] == "aqua")
    assert "Trivy" in aqua["aliases"]
