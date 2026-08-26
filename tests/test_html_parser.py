from pathlib import Path
from app.services.normalization.elements import ElementKind
from app.services.normalization.parsers.html_dom import parse_html

HTML = (Path(__file__).parent / "fixtures" / "comparison_sample.html").read_text(encoding="utf-8")

def test_headings_carry_their_level():
    elements = parse_html(HTML)
    headings = [e for e in elements if e.kind is ElementKind.heading]
    assert [(h.text, h.level) for h in headings] == [("Sonatype vs JFrog", 1), ("Security", 2)]

def test_paragraph_inherits_the_heading_path():
    elements = parse_html(HTML)
    paragraph = next(e for e in elements if e.kind is ElementKind.paragraph)
    assert paragraph.path == ("Sonatype vs JFrog", "Security")

def test_table_rows_preserve_cells_in_order():
    elements = parse_html(HTML)
    rows = [e for e in elements if e.kind is ElementKind.table_row]
    assert rows[1].attrs["cells"] == ["Malware detection", "Fully identifies", "Limited"]

def test_script_nav_and_footer_are_dropped():
    text = " ".join(e.text for e in parse_html(HTML))
    assert "var x" not in text
    assert "Products Pricing" not in text
    assert "© Sonatype" not in text
