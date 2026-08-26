from __future__ import annotations

from app.config.loader import load_config

_WEIGHT_SPECS = [
    {
        "key": "subject_is_jfrog",
        "label": "JFrog is the subject (multiplier)",
        "config_key": ("modifiers", "subject_is_jfrog"),
        "min": 1.0,
        "max": 3.0,
        "step": 0.1,
        "note": (
            "Prioritisation may be biased — visibly and tunably. Lower to ×1.0 to treat "
            "cross-assertions like any other claim."
        ),
        "unit": "multiplier",
    },
    {
        "key": "tier_1_bonus",
        "label": "Tier-1 entity bonus",
        "config_key": ("modifiers", "entity_tier_1"),
        "min": 0,
        "max": 40,
        "step": 1,
        "note": "Deep-coverage competitors (Sonatype) score above shallow-coverage ones.",
        "unit": "points",
    },
    {
        "key": "substantive_bonus",
        "label": "Substantive change bonus",
        "config_key": ("modifiers", "change_kind_substantive"),
        "min": 0,
        "max": 40,
        "step": 1,
        "note": "A real claim change outweighs a cosmetic one.",
        "unit": "points",
    },
    {
        "key": "recency_halflife_days",
        "label": "Recency half-life (days)",
        "config_key": ("recency_halflife_days",),
        "min": 3,
        "max": 45,
        "step": 1,
        "note": "How fast a signal's score decays.",
        "unit": "days",
    },
    {
        "key": "sales_budget",
        "label": "Sales digest budget (items)",
        "config_key": ("budget", "sales"),
        "min": 3,
        "max": 12,
        "step": 1,
        "note": (
            "A hard cap, applied after ranking. A digest that grows without bound is one nobody finishes."
        ),
        "unit": "items",
    },
    {
        "key": "interrupt_cvss",
        "label": "Interrupt CVSS threshold",
        "config_key": ("interrupt", "security_cvss_at_least"),
        "min": 6,
        "max": 10,
        "step": 0.1,
        "note": "Security signals at or above this severity break the daily cadence.",
        "unit": "cvss",
    },
]


def _lookup(cfg, spec: dict) -> float:
    value = cfg.materiality
    for part in spec["config_key"]:
        if part == "modifiers":
            value = value.modifiers
            continue
        if part == "budget":
            value = value.budget
            continue
        if part == "interrupt":
            value = value.interrupt
            continue
        if isinstance(value, dict):
            value = value[part]
        else:
            value = getattr(value, part)
    return float(value)


def get_materiality() -> dict:
    cfg = load_config()
    weights = [
        {
            "key": spec["key"],
            "label": spec["label"],
            "value": _lookup(cfg, spec),
            "min": spec["min"],
            "max": spec["max"],
            "step": spec["step"],
            "note": spec["note"],
            "unit": spec["unit"],
        }
        for spec in _WEIGHT_SPECS
    ]
    return {"config_version": 1, "weights": weights}


def get_watchlist() -> dict:
    cfg = load_config()
    return {"config_version": 1, "terms": list(cfg.watchlist.terms)}
