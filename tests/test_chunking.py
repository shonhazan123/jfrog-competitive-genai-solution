from app.config.loader import load_config
from app.services.normalization.elements import Element, ElementKind
from app.services.ingestion.chunking import chunk_elements

CFG = load_config().chunking

def row(text, order, path=("Comparison",)):
    return Element(ElementKind.table_row, text, order, path=path,
                   attrs={"cells": text.split(" | ")})

def test_a_table_row_is_never_split():
    long_row = row("Malware detection | " + ("x " * 2000) + "| Limited", 0)
    chunks = chunk_elements([long_row], CFG)
    assert len(chunks) == 1                      # oversized, but intact

def test_chunks_do_not_merge_across_a_heading_of_the_configured_level():
    elements = [
        Element(ElementKind.heading, "Security", 0, level=2),
        Element(ElementKind.paragraph, "a " * 50, 1, path=("Security",)),
        Element(ElementKind.heading, "Pricing", 2, level=2),
        Element(ElementKind.paragraph, "b " * 50, 3, path=("Pricing",)),
    ]
    chunks = chunk_elements(elements, CFG)
    assert len(chunks) == 2

def test_every_chunk_carries_a_context_prefix_with_its_section_path():
    chunks = chunk_elements([row("Malware detection | Fully identifies | Limited", 0)], CFG)
    assert "Comparison" in chunks[0].prefix

def test_consecutive_short_elements_group_under_the_budget():
    elements = [Element(ElementKind.paragraph, "short text here", i, path=("S",)) for i in range(5)]
    assert len(chunk_elements(elements, CFG)) == 1
