from app.services.normalization.tracked_page import ComparisonRow
from app.services.detection.structural_diff import diff_rows

def row(dim, jfrog): return ComparisonRow(dimension=dim, cells={"JFrog": jfrog})

def test_no_change_yields_nothing():
    assert diff_rows([row("Malware", "Limited")], [row("Malware", "Limited")]) == []

def test_whitespace_and_case_change_is_cosmetic():
    changes = diff_rows([row("Malware", "Limited")], [row("Malware", "  limited ")])
    assert [c.kind for c in changes] == ["cosmetic"]

def test_reworded_cell_is_substantive_and_carries_before_and_after():
    changes = diff_rows([row("Malware", "Limited")],
                        [row("Malware", "Very limited, not proactive")])
    assert len(changes) == 1
    assert changes[0].kind == "substantive"
    assert changes[0].dimension == "Malware"
    assert changes[0].column == "JFrog"
    assert changes[0].old_value == "Limited"
    assert changes[0].new_value == "Very limited, not proactive"

def test_new_dimension_is_added_and_missing_one_is_removed():
    changes = diff_rows([row("Malware", "Limited")], [row("SBOM", "Export only")])
    assert sorted(c.kind for c in changes) == ["added", "removed"]

def test_row_reordering_is_not_a_change():
    old = [row("Malware", "Limited"), row("SBOM", "Export only")]
    new = [row("SBOM", "Export only"), row("Malware", "Limited")]
    assert diff_rows(old, new) == []
