from dataclasses import dataclass
from app.services.normalization.elements import Element, ElementKind

@dataclass(frozen=True)
class ComparisonRow:
    dimension: str
    cells: dict[str, str]

def extract_comparison_rows(elements: list[Element]) -> list[ComparisonRow]:
    table_rows = [e for e in elements
                  if e.kind is ElementKind.table_row and len(e.attrs.get("cells", [])) >= 2]
    if not table_rows:
        return []

    headers = table_rows[0].attrs["cells"][1:]
    rows: list[ComparisonRow] = []
    for element in table_rows[1:]:
        cells = element.attrs["cells"]
        rows.append(ComparisonRow(
            dimension=cells[0],
            cells={label: value for label, value in zip(headers, cells[1:])},
        ))
    return rows
