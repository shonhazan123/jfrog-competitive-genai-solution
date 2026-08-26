"""In-process config overrides — YAML on disk is read-only at runtime."""

from __future__ import annotations

from copy import deepcopy

from app.config.loader import load_config
from app.config.schema import AppConfig

_materiality_modifiers_override: dict = {}
_watchlist_terms_override: list[str] | None = None
_materiality_config_version: int = 1
_watchlist_config_version: int = 1


class ConfigValidationError(Exception):
    def __init__(self, message: str, code: str = "invalid_config") -> None:
        self.message = message
        self.code = code


def materiality_config_version() -> int:
    return _materiality_config_version


def watchlist_config_version() -> int:
    return _watchlist_config_version


def _deep_merge_modifiers(base: dict, patch: dict) -> dict:
    merged = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def _validate_modifiers(merged: dict) -> None:
    numeric_keys = (
        "subject_is_jfrog",
        "entity_tier_1",
        "change_kind_substantive",
        "corroboration_threshold",
        "corroboration_bonus",
        "watchlist_bonus",
    )
    for key in numeric_keys:
        if key in merged:
            try:
                float(merged[key])
            except (TypeError, ValueError):
                raise ConfigValidationError(f"{key} must be a number")
    grades = merged.get("reliability_grade")
    if isinstance(grades, dict):
        for grade, value in grades.items():
            try:
                float(value)
            except (TypeError, ValueError):
                raise ConfigValidationError(f"reliability_grade.{grade} must be a number")


def apply_materiality_override(overrides: dict) -> None:
    global _materiality_config_version
    base = load_config().materiality.modifiers
    merged_preview = _deep_merge_modifiers(base, _deep_merge_modifiers(_materiality_modifiers_override, overrides))
    _validate_modifiers(merged_preview)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(_materiality_modifiers_override.get(key), dict):
            _materiality_modifiers_override[key] = {
                **_materiality_modifiers_override[key],
                **value,
            }
        else:
            _materiality_modifiers_override[key] = value
    _materiality_config_version += 1


def apply_watchlist_override(terms: list[str]) -> None:
    global _watchlist_config_version
    _watchlist_terms_override = list(terms)
    _watchlist_config_version += 1


def current_config() -> AppConfig:
    base = load_config()
    if not _materiality_modifiers_override and _watchlist_terms_override is None:
        return base
    modifiers = _deep_merge_modifiers(base.materiality.modifiers, _materiality_modifiers_override)
    materiality = base.materiality.model_copy(update={"modifiers": modifiers})
    updates: dict = {"materiality": materiality}
    if _watchlist_terms_override is not None:
        updates["watchlist"] = base.watchlist.model_copy(update={"terms": _watchlist_terms_override})
    return base.model_copy(update=updates)


def clear_overrides() -> None:
    global _materiality_config_version, _watchlist_config_version
    _materiality_modifiers_override.clear()
    _watchlist_terms_override = None
    _materiality_config_version = 1
    _watchlist_config_version = 1
