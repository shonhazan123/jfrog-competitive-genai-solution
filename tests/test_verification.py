from app.config.loader import load_config
from app.services.verification import verify_quote

CFG = load_config().verification

SOURCE = ("Malware detection &mdash; Sonatype fully identifies malicious components as soon as "
          "released. JFrog is “very limited” and not proactive in this area.")

def test_exact_match_after_normalisation_succeeds():
    match = verify_quote("very limited” and not proactive in this area", SOURCE, CFG)
    assert match.ok and match.method == "exact"

def test_entity_and_whitespace_differences_still_match():
    match = verify_quote("released. JFrog is", SOURCE, CFG)
    assert match.ok

def test_the_stored_quote_is_cut_from_the_source_not_the_model_string():
    """The model's string is only a locator. What is stored is always source text."""
    match = verify_quote("VERY LIMITED and not proactive in this area", SOURCE, CFG)
    assert match.ok
    assert match.quote in SOURCE          # literal substring of the capture
    assert match.quote != "VERY LIMITED and not proactive in this area"

def test_a_fabricated_quote_fails():
    match = verify_quote("JFrog will discontinue Artifactory next year", SOURCE, CFG)
    assert match.ok is False and match.method == "failed"

def test_short_quotes_require_exact_match():
    """Fuzzy matching produces false positives on short strings."""
    match = verify_quote("limted", SOURCE, CFG)   # deliberate typo, under min_quote_chars
    assert match.ok is False

def test_offset_is_computed_not_trusted():
    match = verify_quote("fully identifies malicious components", SOURCE, CFG)
    assert match.offset is not None and match.offset >= 0
