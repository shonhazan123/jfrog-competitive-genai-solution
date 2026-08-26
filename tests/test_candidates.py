from app.config.loader import load_config
from app.services.normalization.elements import Element, ElementKind
from app.services.signals.candidates import candidates_from_elements

CFG = load_config().materiality.candidates

def _bullet(text, order): return Element(ElementKind.list_item, text, order, path=("Release 3.95",))

def test_each_bullet_becomes_its_own_candidate():
    elements = [_bullet("Added Cargo registry support with full index mirroring", 0),
                _bullet("Added support for scanning ONNX model artifacts on upload", 1)]
    assert len(candidates_from_elements(elements, CFG)) == 2

def test_short_bullets_are_dropped_as_noise():
    elements = [_bullet("Fixed typo", 0),
                _bullet("Added Cargo registry support with full index mirroring", 1)]
    candidates = candidates_from_elements(elements, CFG)
    assert len(candidates) == 1
    assert "Cargo" in candidates[0].text

def test_candidates_carry_their_section_path():
    candidate = candidates_from_elements([_bullet("Added Cargo registry support with mirroring", 0)], CFG)[0]
    assert candidate.section_path == ("Release 3.95",)

def test_headings_and_table_rows_are_not_candidates():
    elements = [Element(ElementKind.heading, "Release 3.95", 0, level=2),
                Element(ElementKind.table_row, "a │ b", 1, attrs={"cells": ["a", "b"]})]
    assert candidates_from_elements(elements, CFG) == []

def test_candidate_count_is_capped():
    elements = [_bullet(f"Added capability number {i} with a sufficiently long description", i)
                for i in range(200)]
    assert len(candidates_from_elements(elements, CFG)) == CFG.max_candidates_per_document
