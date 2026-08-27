from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.db.session import SessionLocal
from app.models.registry import Entity, Source
from app.models.signal import Signal, SignalEvidence
from app.services.collection.apis.greenhouse import GreenhouseAdapter
from app.services.collection.apis.lever import LeverAdapter
from app.services.collection.apis.osv import OsvAdapter
from app.services.collection.fetcher import StaticFetcher
from app.services.research.competitors import load_competitors
from app.services.research.provenance import index_finding, record_finding
from app.services.scoring.materiality import score

_SUB_TYPES: dict[str, str] = {
    "hiring": "talent_org",
    "pricing": "pricing_packaging",
    "funding": "corporate_financial",
    "security_advisory": "security_trust",
}

_ADAPTERS = {
    "lever": LeverAdapter(),
    "greenhouse": GreenhouseAdapter(),
    "osv": OsvAdapter(),
}


def _api_record_to_dict(record) -> dict:
    return {
        "external_id": record.external_id,
        "title": record.title,
        "body": record.body,
        "occurred_at": record.occurred_at.isoformat() if record.occurred_at else None,
        "url": record.url,
        "extra": dict(record.extra),
    }


def build_targets() -> list[dict]:
    targets: list[dict] = []
    for comp in load_competitors():
        for sub_type, signal_type in _SUB_TYPES.items():
            targets.append(
                {
                    "competitor": comp["slug"],
                    "name": comp["name"],
                    "aliases": comp.get("aliases") or [],
                    "sub_type": sub_type,
                    "signal_type": signal_type,
                }
            )
    return targets


def _query(target: dict) -> str:
    name = target["name"]
    aliases = target.get("aliases") or []
    alias_str = " ".join(aliases)
    sub = target["sub_type"]
    if sub == "hiring":
        return f"{name} careers {alias_str} enterprise sales OR security engineer"
    if sub == "pricing":
        return f"{name} pricing plans per-seat"
    if sub == "funding":
        return f"{name} funding round OR acquisition 2026"
    if sub == "security_advisory":
        return f"{name} {alias_str} security advisory CVE vulnerability"
    return name


def structured_for(session: Session, fetcher=None):
    fetcher = fetcher or StaticFetcher()

    def fn(target: dict) -> list[dict] | None:
        sub = target["sub_type"]
        slug = target["competitor"]
        entity = session.query(Entity).filter_by(slug=slug).one_or_none()
        if entity is None:
            return None

        if sub == "hiring":
            source = (
                session.query(Source)
                .filter(
                    Source.entity_id == entity.id,
                    Source.adapter.in_(["lever", "greenhouse"]),
                    Source.enabled.is_(True),
                )
                .first()
            )
            if source is None:
                return None
            adapter = _ADAPTERS.get(source.adapter or "")
            if adapter is None:
                return None
            return [_api_record_to_dict(r) for r in adapter.collect(source, fetcher)]

        if sub == "security_advisory":
            source = (
                session.query(Source)
                .filter(
                    Source.entity_id == entity.id,
                    Source.adapter == "osv",
                    Source.enabled.is_(True),
                )
                .first()
            )
            if source is None:
                return None
            return [_api_record_to_dict(r) for r in OsvAdapter().collect(source, fetcher)]

        return None

    return fn


def persist_signals(session: Session, drafts: list[dict]) -> int:
    cfg = load_config()
    now = datetime.now(UTC)
    written = 0
    for draft in drafts:
        if draft.get("absent"):
            continue
        entity = session.query(Entity).filter_by(slug=draft["competitor"]).one()
        capture = record_finding(
            session,
            "signals",
            draft["source_url"],
            f'{draft["headline"]}\n{draft["so_what"]}',
        )
        facets = {
            "signal_type": draft["signal_type"],
            "subject_entity": None,
            "asserting_entity": entity.slug,
            "entity_tier": entity.tier,
            "reliability_grade": "C",
            "corroboration_count": 1,
            "capability_tags": draft.get("tags") or [],
            "occurred_at": now,
            "text": draft["headline"],
        }
        cluster_src = f"{draft['competitor']}:{draft['signal_type']}:{draft['headline']}"
        signal = Signal(
            source_id=capture.source_id,
            entity_id=entity.id,
            signal_type=draft["signal_type"],
            headline=draft["headline"][:256],
            occurred_at=now,
            cluster_key=hashlib.sha256(cluster_src.encode()).hexdigest()[:128],
            so_what_sales=draft["so_what"],
            so_what_product=draft["so_what"],
            so_what_exec=draft["so_what"],
            why_it_matters=draft["why_it_matters"],
            capability_tags=draft.get("tags") or [],
            score_sales=score(facets, "sales", cfg).total,
            score_product=score(facets, "product", cfg).total,
            score_exec=score(facets, "exec", cfg).total,
        )
        session.add(signal)
        session.flush()
        session.add(
            SignalEvidence(
                signal_id=signal.id,
                capture_id=capture.id,
                quote=draft["headline"],
                quote_offset=0,
                match_method="synthesis",
            )
        )
        index_finding(
            session,
            record_type="signal",
            record_id=signal.id,
            text=draft["so_what"],
            entity_id=entity.id,
            signal_type=draft["signal_type"],
            published_at=now,
            reliability_grade="C",
        )
        written += 1
    return written


def run_signals() -> dict:
    from agent.graphs.research.signals.deps import SignalCard, SignalsDeps
    from agent.graphs.research.skeleton import run_research
    from agent.llm import get_model
    from agent.tools.web_search import web_search

    gate = get_model("gate").with_structured_output(SignalCard, strict=True)
    with SessionLocal() as session:
        structured = structured_for(session)
        search_fn = lambda t: web_search(_query(t), k=6)
        deps = SignalsDeps(build_targets(), structured, search_fn, gate)
        drafts = run_research(deps)
        n = persist_signals(session, drafts)
        session.commit()
    return {"signals_items": n}
