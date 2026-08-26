import pytest
from pydantic import ValidationError
from agent.schemas import build_extraction_model

MODEL = build_extraction_model(entities=["jfrog", "sonatype", "harbor", "industry"],
                               capability_tags=["malware_detection", "sbom"])

def test_a_competitor_absent_from_config_cannot_be_emitted():
    """Hallucinated entities are structurally impossible, not merely unlikely."""
    with pytest.raises(ValidationError):
        MODEL.model_validate({"signal_type": "product_capability",
                              "asserting_entity": "cloudsmith",   # not in config
                              "subject_entity": None, "mentions_jfrog": False,
                              "headline": "h", "claims": []})

def test_empty_claims_is_valid_because_most_pages_contain_none():
    parsed = MODEL.model_validate({"signal_type": "product_capability",
                                   "asserting_entity": "sonatype", "subject_entity": "sonatype",
                                   "mentions_jfrog": False, "headline": "h", "claims": []})
    assert parsed.claims == []

def test_a_claim_without_a_quote_is_rejected():
    with pytest.raises(ValidationError):
        MODEL.model_validate({"signal_type": "product_capability",
                              "asserting_entity": "sonatype", "subject_entity": "sonatype",
                              "mentions_jfrog": False, "headline": "h",
                              "claims": [{"claim_text": "x", "claim_type": "capability",
                                          "capability_tags": ["sbom"]}]})

def test_an_unknown_capability_tag_is_rejected():
    with pytest.raises(ValidationError):
        MODEL.model_validate({"signal_type": "product_capability",
                              "asserting_entity": "sonatype", "subject_entity": "sonatype",
                              "mentions_jfrog": False, "headline": "h",
                              "claims": [{"claim_text": "x", "quote": "q",
                                          "claim_type": "capability",
                                          "capability_tags": ["telepathy"]}]})
