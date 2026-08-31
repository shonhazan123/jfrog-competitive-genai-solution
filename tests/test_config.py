import pytest
from pydantic import ValidationError
from app.config.schema import VerificationConfig
from app.config.loader import load_config

def test_loads_and_validates_all_config_files(tmp_path):
    config = load_config()
    assert any(e.slug == "sonatype" for e in config.entities)
    assert any(s.mode == "snapshot" for s in config.sources)

def test_rejects_out_of_range_threshold():
    with pytest.raises(ValidationError):
        VerificationConfig.model_validate(
            {"quote_matching": {"fuzzy": {"accept_threshold": 150, "min_quote_chars": 25}}}
        )

def test_gate_call_uses_low_reasoning_effort():
    from app.config.loader import load_config
    assert load_config().llm.calls["gate"].reasoning_effort == "low"

def test_source_registry_excludes_jfrog_and_includes_competitor_feeds():
    cfg = load_config()
    keys = {s.key for s in cfg.sources}
    assert "jfrog_homepage" not in keys
    assert not any(s.entity == "jfrog" for s in cfg.sources)
    expected = {
        "github_changelog",
        "github_blog",
        "gitlab_blog",
        "azure_artifacts_news",
        "cisa_advisories",
    }
    assert expected <= keys
    by_key = {s.key: s for s in cfg.sources}
    assert by_key["github_changelog"].reliability_grade == "A"
    assert by_key["github_blog"].reliability_grade == "B"
    assert by_key["cisa_advisories"].reliability_grade == "A"
    assert set(by_key["gitlab_blog"].covers) == {
        "product_capability",
        "pricing_packaging",
        "positioning_messaging",
    }
