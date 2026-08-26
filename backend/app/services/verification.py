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

    if not fuzzy.enabled or len(normalized_claim) < fuzzy.min_quote_chars:
        return QuoteMatch(False, None, None, "failed")

    size = len(normalized_claim)
    best_score, best_offset = 0.0, -1
    for start, window in _windows(normalized_source, size, max(1, size // 4)):
        score = fuzz.ratio(normalized_claim, window)
        if score > best_score:
            best_score, best_offset = score, start

    if best_score >= fuzzy.accept_threshold and best_offset >= 0:
        return QuoteMatch(True, _cut(source_text, normalized_source, best_offset, size),
                          best_offset, "fuzzy")

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
