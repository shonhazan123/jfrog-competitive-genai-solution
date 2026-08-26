from __future__ import annotations

from typing import Any


def is_primary_source(reliability_grade: str | None) -> bool:
    """Grade-A chunks are treated as primary-source evidence."""
    return reliability_grade == "A"


def evidentiary_boost(row: dict[str, Any], rcfg) -> float:
    grade = row.get("reliability_grade") or ""
    grade_boosts = rcfg.rerank["grade_boost"]
    boost = float(grade_boosts.get(grade, 0.0))
    if is_primary_source(row.get("reliability_grade")):
        boost += float(rcfg.rerank["primary_source_boost"])
    return boost


def rerank_scores(rrf_scores: dict[int, float], chunk_map: dict[int, dict], rcfg) -> list[tuple[dict, float]]:
    scored: list[tuple[dict, float]] = []
    for chunk_id, rrf_score in rrf_scores.items():
        row = chunk_map[chunk_id]
        final = rrf_score + evidentiary_boost(row, rcfg)
        scored.append((row, final))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored
