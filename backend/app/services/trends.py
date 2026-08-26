from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from app.config.schema import TrendConfig

@dataclass(frozen=True)
class Trend:
    theme: str
    direction: Literal["rising", "falling", "steady"]
    velocity: Literal["emerging", "accelerating", "steady", "decaying"]
    signal_count: int
    distinct_sources: int
    confidence: Literal["low", "medium", "high"]
    window_start: date
    window_end: date
    contributing_signal_ids: list[int]

def _confidence(count: int, sources: int, cfg: TrendConfig) -> str:
    if count >= cfg.confidence["high"]["min_signals"] and sources >= cfg.confidence["high"]["min_sources"]:
        return "high"
    if count >= cfg.confidence["medium"]["min_signals"] and sources >= cfg.confidence["medium"]["min_sources"]:
        return "medium"
    return "low"

def compute_trends(signals: list[dict], cfg: TrendConfig, as_of: date) -> list[Trend]:
    """Deterministic aggregation over clustered signal volume.

    Current window vs the preceding window of equal length. Direction is the
    ratio; velocity distinguishes a theme appearing from nothing (emerging)
    from one already present and speeding up (accelerating).
    """
    now = datetime.now(UTC)
    window = timedelta(weeks=cfg.window_weeks)
    current_start, prior_start = now - window, now - (window * 2)

    current: dict[str, list[dict]] = defaultdict(list)
    prior: dict[str, list[dict]] = defaultdict(list)
    for signal in signals:
        occurred = signal["occurred_at"]
        bucket = current if occurred >= current_start else (prior if occurred >= prior_start else None)
        if bucket is None:
            continue
        for theme in signal.get("capability_tags") or ["_untagged"]:
            bucket[theme].append(signal)

    trends: list[Trend] = []
    for theme, items in current.items():
        if len(items) < cfg.min_signals_for_trend:
            continue
        prior_count = len(prior.get(theme, []))
        ratio = len(items) / prior_count if prior_count else float("inf")

        if ratio >= cfg.direction["rising_ratio"]:
            direction = "rising"
        elif ratio <= cfg.direction["falling_ratio"]:
            direction = "falling"
        else:
            direction = "steady"

        if prior_count <= cfg.velocity["emerging_prior_max"]:
            velocity = "emerging"
        elif ratio >= cfg.velocity["accelerating_ratio"]:
            velocity = "accelerating"
        elif direction == "falling":
            velocity = "decaying"
        else:
            velocity = "steady"

        sources = {s["source_id"] for s in items}
        trends.append(Trend(
            theme=theme, direction=direction, velocity=velocity,
            signal_count=len(items), distinct_sources=len(sources),
            confidence=_confidence(len(items), len(sources), cfg),
            window_start=(now - window).date(), window_end=as_of,
            contributing_signal_ids=[s["id"] for s in items],
        ))

    return sorted(trends, key=lambda t: (-t.signal_count, t.theme))
