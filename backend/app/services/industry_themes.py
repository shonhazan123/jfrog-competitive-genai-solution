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


def _load_buckets() -> list[dict]:
    data = yaml.safe_load(
        (Path(settings.config_dir) / "industry_buckets.yaml").read_text(encoding="utf-8")
    )
    return data["buckets"]


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


def _bucket_by_key(buckets: list[dict], key: str) -> dict | None:
    if key == _OTHER_THEME["key"]:
        return _OTHER_THEME
    return next((b for b in buckets if b["key"] == key), None)


def list_themes(session: Session) -> list[dict]:
    buckets = _load_buckets()
    signals = fetch_active_industry_signals(session)
    grouped: dict[str, list[dict]] = {b["key"]: [] for b in buckets}
    other_items: list[dict] = []

    for signal in signals:
        item = build_industry_item(session, signal)
        key = signal.theme_key
        if key is None or key not in grouped:
            other_items.append(item)
        else:
            grouped[key].append(item)

    result: list[dict] = []
    for bucket in buckets:
        count = len(grouped[bucket["key"]])
        label = bucket["label"]
        result.append(
            {
                "key": bucket["key"],
                "label": label,
                "count": count,
                "state_of_play": f"{count} items — {label}",
                "jfrog_relevance": bucket.get("jfrog_relevance", ""),
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
    buckets = _load_buckets()
    bucket = _bucket_by_key(buckets, key)
    if bucket is None:
        raise KeyError(key)

    signals = fetch_active_industry_signals(session)
    items: list[dict] = []
    for signal in signals:
        item = build_industry_item(session, signal)
        if key == _OTHER_THEME["key"]:
            if signal.theme_key is None or signal.theme_key not in {b["key"] for b in buckets}:
                items.append(item)
        elif signal.theme_key == key:
            items.append(item)

    label = bucket["label"]
    return {
        "label": label,
        "synthesis": f"{len(items)} items grouped under {label}.",
        "jfrog_relevance": bucket.get("jfrog_relevance", ""),
        "items": items,
    }
