from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import select

from app.models.registry import Entity
from app.services.config_overrides import (
    apply_materiality_override,
    apply_watchlist_override,
    ConfigValidationError,
    current_config,
    materiality_config_version,
    watchlist_config_version,
)
from app.services.scoring.rescore import rescore_all_signals
from app.settings import settings

_instructions_override: list[str] | None = None
_instructions_config_version: int = 1
_competitors_config_version: int = 1


def _load_instructions_yaml() -> list[str]:
    p = Path(settings.config_dir) / "instructions.yaml"
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return list(data.get("instructions", []))


def current_instructions() -> list[str]:
    if _instructions_override is not None:
        return list(_instructions_override)
    return _load_instructions_yaml()


def instructions_config_version() -> int:
    return _instructions_config_version


def apply_instructions_override(instructions: list[str]) -> None:
    global _instructions_config_version, _instructions_override
    _instructions_override = list(instructions)
    _instructions_config_version += 1


def competitors_config_version() -> int:
    return _competitors_config_version


def clear_config_extensions() -> None:
    global _instructions_override, _instructions_config_version, _competitors_config_version
    _instructions_override = None
    _instructions_config_version = 1
    _competitors_config_version = 1

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


def get_instructions() -> dict:
    return {
        "config_version": instructions_config_version(),
        "instructions": current_instructions(),
    }


def update_instructions(session, body: dict) -> dict:
    instructions = body.get("instructions")
    if not isinstance(instructions, list):
        raise ConfigValidationError("instructions must be a list of strings")
    if not all(isinstance(line, str) for line in instructions):
        raise ConfigValidationError("instructions must be a list of strings")
    apply_instructions_override(instructions)
    return get_instructions()


def get_competitors(session) -> dict:
    rows = session.execute(
        select(Entity).where(Entity.kind == "competitor").order_by(Entity.slug)
    ).scalars().all()
    return {
        "config_version": competitors_config_version(),
        "competitors": [{"slug": row.slug, "name": row.name} for row in rows],
    }


def update_competitors(session, body: dict) -> dict:
    global _competitors_config_version
    competitors = body.get("competitors")
    if not isinstance(competitors, list):
        raise ConfigValidationError("competitors must be a list")
    for item in competitors:
        if not isinstance(item, dict):
            raise ConfigValidationError("each competitor must be an object with slug and name")
        slug = item.get("slug")
        name = item.get("name")
        if not slug or not name:
            raise ConfigValidationError("each competitor requires slug and name")
        existing = session.execute(select(Entity).where(Entity.slug == slug)).scalar_one_or_none()
        if existing is None:
            session.add(
                Entity(slug=slug, name=name, kind="competitor", tier=2, aliases=[])
            )
    session.flush()
    _competitors_config_version += 1
    return get_competitors(session)
