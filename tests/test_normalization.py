from app.services.normalization.clean import normalize_text
from app.services.detection.hashing import content_hash, normalized_hash

def test_decodes_entities_and_normalises_quotes():
    assert normalize_text("JFrog&nbsp;&amp; \u201cNexus\u201d") == 'jfrog & "nexus"'

def test_collapses_whitespace_and_strips_zero_width():
    assert normalize_text("a\u200b  b\n\nc") == "a b c"

def test_cosmetic_change_produces_the_same_normalised_hash():
    a = normalized_hash("Malware detection:  Limited")
    b = normalized_hash("Malware   detection: Limited\n")
    assert a == b

def test_substantive_change_produces_a_different_hash():
    a = normalized_hash("Malware detection: Limited")
    b = normalized_hash("Malware detection: Very limited, not proactive")
    assert a != b

def test_content_hash_is_stable_and_hex():
    digest = content_hash(b"abc")
    assert digest == content_hash(b"abc")
    assert len(digest) == 64
