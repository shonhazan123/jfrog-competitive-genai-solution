from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.controllers.signals import _signal_evidence
from app.models.registry import Entity, Source
from app.models.signal import Signal
from app.serializers.common import fmt_ts, signal_type_label
from app.settings import settings

_STANDARD_CHIPS = {
    "market_regulatory": "EU CRA",
    "security_trust": "SUPPLY CHAIN",
    "partnership_ecosystem": "CNCF",
    "product_capability": "SLSA",
}

_OTHER_THEME = {"key": "other", "label": "Other", "jfrog_relevance": ""}


def _load_themes() -> list[dict]:
    data = yaml.safe_load((Path(settings.config_dir) / "themes.yaml").read_text(encoding="utf-8"))
    return data["themes"]


def _fallback_evidence(signal: Signal) -> dict:
    from app.services.citation import DeliveryRecord, build_citation, citation_to_dict

    return {
        "quote": signal.headline,
        "source_url": "",
        "source_name": "Industry",
        "captured_at": fmt_ts(signal.occurred_at),
        "reliability_grade": "A",
        "credibility_score": 2,
        "is_primary": True,
        "citation": citation_to_dict(
            build_citation(
                DeliveryRecord(
                    source_name="Industry",
                    source_url="",
                    fetched_at=signal.occurred_at,
                )
            )
        ),
    }


def fetch_active_industry_signals(session: Session, *, limit: int | None = None) -> list[Signal]:
    industry = session.query(Entity).filter_by(slug="industry").one_or_none()
    if industry is None:
        return []

    query = (
        session.query(Signal)
        .filter(Signal.entity_id == industry.id, Signal.status == "active")
        .order_by(Signal.occurred_at.desc())
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def build_industry_item(session: Session, signal: Signal) -> dict:
    cfg = load_config()
    evidence_list = _signal_evidence(session, signal)
    evidence = evidence_list[0] if evidence_list else _fallback_evidence(signal)
    return {
        "id": f"ind_{signal.id}",
        "standard_chip": _STANDARD_CHIPS.get(signal.signal_type, "SUPPLY CHAIN"),
        "signal_type": signal.signal_type,
        "signal_type_label": signal_type_label(signal.signal_type, cfg),
        "handling_label": None,
        "headline": signal.headline,
        "body": signal.so_what_product or signal.so_what_sales or signal.headline,
        "occurred_at": fmt_ts(signal.occurred_at),
        "evidence": evidence,
    }


def _source_covers(session: Session, signal: Signal) -> list[str]:
    """The source's `covers` hint, used only for theme routing — kept out of the
    public industry item so the API response shape stays stable."""
    source = session.query(Source).filter_by(id=signal.source_id).one_or_none()
    return list(source.covers) if source and source.covers else []


def _routing_item(session: Session, signal: Signal, item: dict) -> dict:
    """Augment an item with the source `covers` hint for `assign_theme` only."""
    return {**item, "covers": _source_covers(session, signal)}


def assign_theme(item: dict, themes: list[dict]) -> str | None:
    signal_type = item.get("signal_type")
    headline = item.get("headline") or ""
    body = item.get("body") or ""
    text = f"{headline} {body}".lower()

    for theme in themes:
        match = theme.get("match") or {}
        signal_types = match.get("signal_types") or []
        if signal_type not in signal_types:
            continue

        keywords = match.get("keywords") or []
        if not keywords:
            return theme["key"]

        if any(keyword.lower() in text for keyword in keywords):
            return theme["key"]

        covers = item.get("covers") or []
        if any(cover in signal_types for cover in covers):
            return theme["key"]

    return None


def _theme_by_key(themes: list[dict], key: str) -> dict | None:
    if key == _OTHER_THEME["key"]:
        return _OTHER_THEME
    return next((theme for theme in themes if theme["key"] == key), None)


def list_themes(session: Session) -> list[dict]:
    themes = _load_themes()
    signals = fetch_active_industry_signals(session)
    buckets: dict[str, list[dict]] = {theme["key"]: [] for theme in themes}
    other_items: list[dict] = []

    for signal in signals:
        item = build_industry_item(session, signal)
        key = assign_theme(_routing_item(session, signal, item), themes)
        if key is None:
            other_items.append(item)
        else:
            buckets[key].append(item)

    result: list[dict] = []
    for theme in themes:
        count = len(buckets[theme["key"]])
        label = theme["label"]
        result.append(
            {
                "key": theme["key"],
                "label": label,
                "count": count,
                "state_of_play": f"{count} items — {label}",
                "jfrog_relevance": theme.get("jfrog_relevance", ""),
            }
        )

    if other_items:
        count = len(other_items)
        label = _OTHER_THEME["label"]
        result.append(
            {
                "key": _OTHER_THEME["key"],
                "label": label,
                "count": count,
                "state_of_play": f"{count} items — {label}",
                "jfrog_relevance": _OTHER_THEME["jfrog_relevance"],
            }
        )

    return result


def theme_detail(session: Session, key: str) -> dict:
    themes = _load_themes()
    theme = _theme_by_key(themes, key)
    if theme is None:
        raise KeyError(key)

    signals = fetch_active_industry_signals(session)
    items: list[dict] = []
    for signal in signals:
        item = build_industry_item(session, signal)
        assigned = assign_theme(_routing_item(session, signal, item), themes)
        if key == _OTHER_THEME["key"]:
            if assigned is None:
                items.append(item)
        elif assigned == key:
            items.append(item)

    label = theme["label"]
    return {
        "label": label,
        "synthesis": f"{len(items)} items grouped under {label}.",
        "jfrog_relevance": theme.get("jfrog_relevance", ""),
        "items": items,
    }
