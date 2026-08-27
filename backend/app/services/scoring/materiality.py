import math
from dataclasses import dataclass
from datetime import UTC, datetime
from app.config.schema import AppConfig

@dataclass(frozen=True)
class ScoreBreakdown:
    total: float
    parts: list[tuple[str, float]]

def _watchlist_hits(text: str, terms: list[str]) -> list[str]:
    lowered = (text or "").lower()
    return [t for t in terms if t.lower() in lowered]

def score(facets: dict, persona: str, config: AppConfig) -> ScoreBreakdown:
    """Deterministic, explainable, and tunable without touching code.

    The model assigned the labels in `facets`. This function applies the team's
    dissemination policy to them. Re-scoring the entire ledger after a weight
    change is a SQL update, not re-inference.
    """
    materiality, modifiers = config.materiality, config.materiality.modifiers
    relevance = config.routing.matrix[facets["signal_type"]][persona]

    parts: list[tuple[str, float]] = [("base", relevance * materiality.base_multiplier)]
    base = parts[0][1]

    if facets.get("subject_entity") == "jfrog" and persona == "sales":
        parts.append(("about_jfrog", base * (modifiers["subject_is_jfrog"] - 1.0)))
    if facets.get("entity_tier") == 1:
        parts.append(("tier_1", modifiers["entity_tier_1"]))
    if facets.get("change_kind") == "substantive":
        parts.append(("substantive_change", modifiers["change_kind_substantive"]))
    if facets.get("corroboration_count", 1) >= modifiers["corroboration_threshold"]:
        parts.append(("corroborated", modifiers["corroboration_bonus"]))
    if hits := _watchlist_hits(facets.get("text", ""), config.watchlist.terms):
        parts.append((f"watchlist:{','.join(hits)}", modifiers["watchlist_bonus"]))

    parts.append(("source_grade", modifiers["reliability_grade"][facets["reliability_grade"]]))

    occurred = facets.get("occurred_at")
    if occurred:
        age_days = (datetime.now(UTC) - occurred).total_seconds() / 86400
        decay = base * (math.pow(0.5, age_days / materiality.recency_halflife_days) - 1.0)
        parts.append(("recency", decay))

    return ScoreBreakdown(total=sum(v for _, v in parts), parts=parts)


_TIE_ORDER = {"exec": 3, "product": 2, "sales": 1}
_TIER_PRIORITY = {"act_on_it": 3, "worth_knowing": 2, "background": 1}


def tier_priority(tier: str) -> int:
    return _TIER_PRIORITY.get(tier, 0)


def tier_for(total: float, config: AppConfig) -> str:
    t = config.materiality.tiers
    if total >= t["act_on_it"]:
        return "act_on_it"
    if total >= t["worth_knowing"]:
        return "worth_knowing"
    return "background"


def primary_stakeholder(scores: dict[str, float]) -> str:
    return max(scores, key=lambda p: (scores[p], _TIE_ORDER[p]))
