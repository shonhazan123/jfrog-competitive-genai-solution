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

def test_extract_call_uses_low_reasoning_effort():
    from app.config.loader import load_config
    assert load_config().llm.calls["extract"].reasoning_effort == "low"
