from dataclasses import dataclass
from app.config.schema import CandidateConfig
from app.services.normalization.elements import Element, ElementKind

CANDIDATE_KINDS = (ElementKind.list_item, ElementKind.paragraph)

@dataclass(frozen=True)
class Candidate:
    text: str
    section_path: tuple[str, ...]
    order: int
    source_ref: str

def candidates_from_elements(elements: list[Element], cfg: CandidateConfig) -> list[Candidate]:
    """One candidate per bullet or paragraph. A 40-bullet release yields up to 40
    candidates, not one signal — most will classify as no_signal and be dropped."""
    candidates = [
        Candidate(text=e.text, section_path=e.path, order=e.order,
                  source_ref=" > ".join(e.path) if e.path else "")
        for e in elements
        if e.kind in CANDIDATE_KINDS and len(e.text) >= cfg.min_candidate_chars
    ]
    return candidates[: cfg.max_candidates_per_document]
