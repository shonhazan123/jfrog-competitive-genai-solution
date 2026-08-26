from __future__ import annotations

from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.models.registry import Entity
from app.models.signal import Signal
from app.controllers.signals import _signal_evidence
from app.serializers.common import fmt_ts, signal_type_label

_STANDARD_CHIPS = {
    "market_regulatory": "EU CRA",
    "security_trust": "SUPPLY CHAIN",
    "partnership_ecosystem": "CNCF",
    "product_capability": "SLSA",
}


def list_industry(session: Session, limit: int = 50) -> dict:
    cfg = load_config()
    industry = session.query(Entity).filter_by(slug="industry").one_or_none()
    if industry is None:
        return {"items": [], "total": 0, "cursor": None}

    signals = (
        session.query(Signal)
        .filter(Signal.entity_id == industry.id, Signal.status == "active")
        .order_by(Signal.occurred_at.desc())
        .limit(limit)
        .all()
    )
    items = []
    for signal in signals:
        evidence_list = _signal_evidence(session, signal)
        evidence = evidence_list[0] if evidence_list else None
        if evidence is None:
            from app.services.citation import DeliveryRecord, build_citation, citation_to_dict

            evidence = {
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
        items.append(
            {
                "id": f"ind_{signal.id}",
                "standard_chip": _STANDARD_CHIPS.get(signal.signal_type, "SUPPLY CHAIN"),
                "signal_type": signal.signal_type,
                "signal_type_label": signal_type_label(signal.signal_type, cfg),
                "headline": signal.headline,
                "body": signal.so_what_product or signal.so_what_sales or signal.headline,
                "occurred_at": fmt_ts(signal.occurred_at),
                "evidence": evidence,
            }
        )
    return {"items": items, "total": len(items), "cursor": None}
