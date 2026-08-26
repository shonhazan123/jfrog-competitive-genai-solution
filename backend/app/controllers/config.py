from __future__ import annotations

from app.services.config_overrides import (
    apply_materiality_override,
    apply_watchlist_override,
    ConfigValidationError,
    current_config,
    materiality_config_version,
    watchlist_config_version,
)
from app.services.scoring.rescore import rescore_all_signals

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
    cfg = current_config()
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
    return {"config_version": materiality_config_version(), "weights": weights}


def get_watchlist() -> dict:
    cfg = current_config()
    return {"config_version": watchlist_config_version(), "terms": list(cfg.watchlist.terms)}


def _weight_patch(body: dict) -> dict:
    modifiers: dict = {}
    key_to_spec = {spec["key"]: spec for spec in _WEIGHT_SPECS}
    for item in body.get("weights", []):
        spec = key_to_spec.get(item["key"])
        if spec is None:
            raise ConfigValidationError(f"Unknown weight key: {item['key']}")
        value = item["value"]
        config_key = spec["config_key"]
        if config_key[0] == "modifiers" and len(config_key) == 2:
            modifiers[config_key[1]] = value
        else:
            raise ConfigValidationError(f"Weight {item['key']} cannot be updated via modifiers")
    return modifiers


def update_materiality(session, body: dict) -> dict:
    modifier_patch: dict = dict(body.get("modifiers", {}))
    if "weights" in body:
        modifier_patch = {**modifier_patch, **_weight_patch(body)}
    if not modifier_patch:
        raise ConfigValidationError("No materiality overrides supplied")
    apply_materiality_override(modifier_patch)
    rescore_all_signals(session)
    return get_materiality()


def update_watchlist(session, body: dict) -> dict:
    terms = body.get("terms")
    if not isinstance(terms, list):
        raise ConfigValidationError("terms must be a list of strings")
    apply_watchlist_override(terms)
    rescore_all_signals(session)
    return get_watchlist()
