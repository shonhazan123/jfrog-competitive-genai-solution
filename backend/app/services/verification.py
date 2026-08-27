from dataclasses import dataclass
from rapidfuzz import fuzz
from app.config.schema import VerificationConfig
from app.services.normalization.clean import normalize_text

# Above this raw length the exhaustive fuzzy window scan (O(len(text) * window)) becomes the
# dominant cost of the whole interpret pipeline — a single ~400k-char homepage capture spent
# >10 min in verify. For large captures we first locate the best-matching region with a
# C-level partial-ratio alignment, then run the exact same window scan only around that
# anchor. Small captures (all verification fixtures/tests) keep the original full scan, so
# match results and offsets are unchanged for them.
_FUZZY_FULL_SCAN_LIMIT = 4000
_FUZZY_ANCHOR_PAD = 4000

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

def _scan_start_range(source_text: str, fuzzy_source: str, fuzzy_claim: str, hi: int) -> range:
    """Start offsets for the fuzzy window scan.

    Small captures scan the whole document (identical to the original algorithm, so
    verification fixtures are unaffected). Large captures use a C-level partial-ratio
    alignment to find the best-matching region, then scan a generous neighbourhood around
    that anchor — turning a multi-minute full scan into a sub-second one while still running
    the exact same window/offset logic over the real source text.
    """
    if len(source_text) <= _FUZZY_FULL_SCAN_LIMIT or not fuzzy_source:
        return range(len(source_text))
    alignment = fuzz.partial_ratio_alignment(fuzzy_claim, fuzzy_source)
    if alignment is None:
        return range(len(source_text))
    # Normalisation only collapses whitespace, so position within the normalised source maps
    # near-proportionally onto the raw source; the wide pad absorbs uneven whitespace.
    approx = int(alignment.dest_start * len(source_text) / max(1, len(fuzzy_source)))
    start_lo = max(0, approx - _FUZZY_ANCHOR_PAD)
    start_hi = min(len(source_text), approx + len(fuzzy_claim) + hi + _FUZZY_ANCHOR_PAD)
    return range(start_lo, start_hi)

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

    start_range = _scan_start_range(source_text, fuzzy_source, fuzzy_claim, hi)

    best_score, best_span, best_offset = 0.0, None, -1
    for start in start_range:
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

    Small captures walk from the start (unchanged, so fixtures/tests are unaffected). Large
    captures start at the proportional anchor and search outward: sanitized text is already
    whitespace-collapsed, so the normalised offset maps almost 1:1 onto the raw offset and the
    matching span is found in a handful of steps instead of re-normalising the whole document
    for every verified claim (previously ~30s per claim on a 40k-char page).
    """
    target = normalized[offset:offset + length]
    for start in _cut_start_sequence(len(original), len(normalized), offset):
        for end in range(start + length, min(len(original), start + length * 3) + 1):
            if normalize_text(original[start:end]) == target:
                return original[start:end]
    return target

def _cut_start_sequence(original_len: int, normalized_len: int, offset: int):
    """Candidate start offsets for `_cut`, ordered so the true span is reached fast."""
    if original_len <= _FUZZY_FULL_SCAN_LIMIT or normalized_len == 0:
        return range(original_len)
    anchor = min(max(0, offset * original_len // normalized_len), original_len - 1)
    lo = max(0, anchor - _FUZZY_ANCHOR_PAD)
    hi = min(original_len, anchor + _FUZZY_ANCHOR_PAD)
    sequence = [anchor]
    for delta in range(1, hi - lo):
        if anchor - delta >= lo:
            sequence.append(anchor - delta)
        if anchor + delta < hi:
            sequence.append(anchor + delta)
    return sequence
