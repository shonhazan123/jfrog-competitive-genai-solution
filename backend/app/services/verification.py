from dataclasses import dataclass
from rapidfuzz import fuzz
from app.config.schema import VerificationConfig
from app.services.normalization.clean import normalize_text

@dataclass(frozen=True)
class QuoteMatch:
    ok: bool
    quote: str | None
    offset: int | None
    method: str            # exact | fuzzy | failed

def _windows(text: str, size: int, step: int):
    for start in range(0, max(1, len(text) - size + 1), step):
        yield start, text[start:start + size]

def _fuzzy_normalize(s: str) -> str:
    return normalize_text(s).replace('"', "").replace("'", "")

def verify_quote(claimed: str, source_text: str, cfg: VerificationConfig) -> QuoteMatch:
    """Locate the model's quote in the source and return SOURCE TEXT, never the
    model's string. The model points; we cut."""
    fuzzy = cfg.quote_matching.fuzzy
    normalized_source = normalize_text(source_text)
    normalized_claim = normalize_text(claimed)

    if not normalized_claim:
        return QuoteMatch(False, None, None, "failed")

    offset = normalized_source.find(normalized_claim)
    if offset >= 0:
        return QuoteMatch(True, _cut(source_text, normalized_source, offset,
                                     len(normalized_claim)), offset, "exact")

    fuzzy_source = _fuzzy_normalize(source_text)
    fuzzy_claim = _fuzzy_normalize(claimed)

    if not fuzzy.enabled or len(fuzzy_claim) < fuzzy.min_quote_chars:
        return QuoteMatch(False, None, None, "failed")

    lo = max(1, len(fuzzy_claim) - 5)
    hi = len(fuzzy_claim) + 10
    best_score, best_span, best_offset = 0.0, None, -1
    for start in range(len(source_text)):
        for end in range(start + lo, min(len(source_text), start + hi) + 1):
            span = source_text[start:end]
            score = fuzz.ratio(fuzzy_claim, _fuzzy_normalize(span))
            if score > best_score:
                best_score, best_span, best_offset = score, span, start

    if best_score >= fuzzy.accept_threshold and best_span is not None:
        norm_offset = normalized_source.find(normalize_text(best_span))
        return QuoteMatch(True, best_span, norm_offset if norm_offset >= 0 else best_offset, "fuzzy")

    return QuoteMatch(False, None, None, "failed")

def _cut(original: str, normalized: str, offset: int, length: int) -> str:
    """Map a normalised offset back to the original text conservatively.

    Normalisation only ever shortens (collapsing whitespace, stripping zero-width),
    so the original span is at least as long. Walk forward until the normalised form
    of the candidate span matches.
    """
    target = normalized[offset:offset + length]
    for start in range(len(original)):
        for end in range(start + length, min(len(original), start + length * 3) + 1):
            if normalize_text(original[start:end]) == target:
                return original[start:end]
    return target
