from __future__ import annotations

from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.services.coverage import build_coverage_matrix

_COVERAGE_CAPTION = (
    "This grid answers the one question a competitor tracker must be able to answer: "
    "what are we blind to? Collection must be unbiased even though prioritisation is not — "
    "an empty cell is a configured gap, made visible rather than assumed away."
)

_COVERAGE_LEGEND = [
    ["✓✓", "multiple sources"],
    ["✓", "one source"],
    ["✗", "configured gap — no source yet"],
    ["—", "not applicable for this entity"],
]

_COLUMN_LABELS = {
    "product_capability": "product",
    "security_trust": "security",
    "market_regulatory": "market/reg",
    "partnership_ecosystem": "partnership",
    "talent_org": "talent",
    "customer_evidence": "customer",
    "positioning_messaging": "positioning",
    "pricing_packaging": "pricing",
    "corporate_financial": "corporate",
}


def get_coverage_matrix(session: Session) -> dict:
    cfg = load_config()
    matrix = build_coverage_matrix(session, cfg)
    columns = [_COLUMN_LABELS.get(col, col) for col in matrix.columns]
    rows = []
    for row in matrix.rows:
        cells = [
            {
                "signal_type": cell.signal_type,
                "status": cell.status,
                "source_count": cell.source_count,
            }
            for cell in row.cells.values()
        ]
        rows.append({"entity": row.entity, "tier": row.tier, "cells": cells})
    return {
        "caption": _COVERAGE_CAPTION,
        "columns": columns,
        "rows": rows,
        "legend": _COVERAGE_LEGEND,
    }
