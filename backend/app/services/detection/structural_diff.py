from dataclasses import dataclass
from typing import Literal
from app.services.normalization.clean import normalize_text
from app.services.normalization.tracked_page import ComparisonRow

ChangeKind = Literal["added", "removed", "substantive", "cosmetic"]

@dataclass(frozen=True)
class RowChange:
    dimension: str
    column: str
    old_value: str | None
    new_value: str | None
    kind: ChangeKind

def _key(dimension: str) -> str:
    return normalize_text(dimension)

def diff_rows(old: list[ComparisonRow], new: list[ComparisonRow]) -> list[RowChange]:
    """Compare by dimension key, so row reordering is not reported as a change."""
    old_by_key = {_key(r.dimension): r for r in old}
    new_by_key = {_key(r.dimension): r for r in new}
    changes: list[RowChange] = []

    for key, new_row in new_by_key.items():
        old_row = old_by_key.get(key)
        if old_row is None:
            for column, value in new_row.cells.items():
                changes.append(RowChange(new_row.dimension, column, None, value, "added"))
            continue
        for column, new_value in new_row.cells.items():
            old_value = old_row.cells.get(column)
            if old_value == new_value:
                continue
            if old_value is not None and normalize_text(old_value) == normalize_text(new_value):
                kind: ChangeKind = "cosmetic"
            else:
                kind = "substantive" if old_value is not None else "added"
            changes.append(RowChange(new_row.dimension, column, old_value, new_value, kind))

    for key, old_row in old_by_key.items():
        if key not in new_by_key:
            for column, value in old_row.cells.items():
                changes.append(RowChange(old_row.dimension, column, value, None, "removed"))

    return changes
