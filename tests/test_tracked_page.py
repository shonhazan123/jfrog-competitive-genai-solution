from pathlib import Path
from app.services.normalization.parsers.html_dom import parse_html
from app.services.normalization.tracked_page import extract_comparison_rows

HTML = (Path(__file__).parent / "fixtures" / "comparison_sample.html").read_text(encoding="utf-8")

def test_first_row_becomes_column_headers_not_a_row():
    rows = extract_comparison_rows(parse_html(HTML))
    assert [r.dimension for r in rows] == ["Malware detection", "SBOM"]

def test_cells_are_keyed_by_column_label():
    rows = extract_comparison_rows(parse_html(HTML))
    assert rows[0].cells == {"Sonatype": "Fully identifies", "JFrog": "Limited"}

def test_rows_with_a_single_cell_are_ignored():
    from app.services.normalization.elements import Element, ElementKind
    lone = [Element(ElementKind.table_row, "x", 0, attrs={"cells": ["x"]})]
    assert extract_comparison_rows(lone) == []
