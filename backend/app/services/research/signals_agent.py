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
from app.services.research.dedup import dedupe_items
from app.services.research.provenance import index_finding, record_finding, sanitize_text
from app.services.scoring.materiality import score
from agent.graphs.research.query import broaden_query, dedupe_names

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


def _query(target: dict, attempt: int = 1) -> str:
    names = dedupe_names(target["name"], target.get("aliases") or [])
    primary = names[0] if names else target["name"]
    alias_str = " ".join(names[1:])
    sub = target["sub_type"]
    if sub == "hiring":
        base = f"{primary} careers {alias_str} enterprise sales OR security engineer".strip()
    elif sub == "pricing":
        base = f"{primary} pricing plans per-seat"
    elif sub == "funding":
        base = f"{primary} funding round OR acquisition 2026"
    elif sub == "security_advisory":
        base = f"{primary} {alias_str} security advisory CVE vulnerability".strip()
    else:
        base = primary
    return broaden_query(base, attempt)


def _structured_collect(session: Session, target: dict, fetcher) -> list[dict] | None:
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


def structured_for(session: Session | None = None, fetcher=None):
    """Return a structured-source collector for one target.

    When session is omitted, each call opens its own SessionLocal so the
    skeleton can resolve targets concurrently without sharing SQLAlchemy state.
    """
    fetcher = fetcher or StaticFetcher()

    def fn(target: dict) -> list[dict] | None:
        if session is not None:
            return _structured_collect(session, target, fetcher)
        with SessionLocal() as own_session:
            return _structured_collect(own_session, target, fetcher)

    return fn


def persist_signals(session: Session, drafts: list[dict]) -> int:
    cfg = load_config()
    now = datetime.now(UTC)

    # Pass 1 — record every finding's capture and build a clusterable item.
    items: list[dict] = []
    for draft in drafts:
        if draft.get("absent"):
            continue
        headline = sanitize_text(draft["headline"])
        so_what = sanitize_text(draft["so_what"])
        why_it_matters = sanitize_text(draft["why_it_matters"])
        entity = session.query(Entity).filter_by(slug=draft["competitor"]).one()
        capture = record_finding(
            session,
            "signals",
            draft["source_url"],
            f"{headline}\n{so_what}",
        )
        items.append({
            "entity": entity,
            "entity_slug": entity.slug,
            "signal_type": draft["signal_type"],
            "headline": headline,
            "so_what": so_what,
            "why_it_matters": why_it_matters,
            "tags": draft.get("tags") or [],
            "capture": capture,
            "occurred_at": now,
        })

    # Pass 2 — one Signal per event; the N framings become N evidence rows and
    # the corroboration count, which feeds the materiality corroboration bonus.
    written = 0
    for group in dedupe_items(items, cfg.materiality.cluster):
        rep = group[0]
        entity = rep["entity"]
        headline = rep["headline"]
        corroboration = len(group)
        facets = {
            "signal_type": rep["signal_type"],
            "subject_entity": None,
            "asserting_entity": entity.slug,
            "entity_tier": entity.tier,
            "reliability_grade": "C",
            "corroboration_count": corroboration,
            "capability_tags": rep["tags"],
            "occurred_at": now,
            "text": headline,
        }
        cluster_src = f"{entity.slug}:{rep['signal_type']}:{headline}"
        signal = Signal(
            source_id=rep["capture"].source_id,
            entity_id=entity.id,
            signal_type=rep["signal_type"],
            headline=headline[:256],
            occurred_at=now,
            cluster_key=hashlib.sha256(cluster_src.encode()).hexdigest()[:128],
            corroboration_count=corroboration,
            so_what_sales=rep["so_what"],
            so_what_product=rep["so_what"],
            so_what_exec=rep["so_what"],
            why_it_matters=rep["why_it_matters"],
            capability_tags=rep["tags"],
            score_sales=score(facets, "sales", cfg).total,
            score_product=score(facets, "product", cfg).total,
            score_exec=score(facets, "exec", cfg).total,
        )
        session.add(signal)
        session.flush()
        for member in group:
            session.add(
                SignalEvidence(
                    signal_id=signal.id,
                    capture_id=member["capture"].id,
                    quote=member["headline"],
                    quote_offset=0,
                    match_method="synthesis",
                )
            )
        index_finding(
            session,
            record_type="signal",
            record_id=signal.id,
            text=rep["so_what"],
            entity_id=entity.id,
            signal_type=rep["signal_type"],
            published_at=now,
            reliability_grade="C",
            url=rep["capture"].blob_path,
        )
        written += 1
    return written


def run_signals(progress=None) -> dict:
    from agent.graphs.research.signals.deps import SignalCard, SignalsDeps
    from agent.graphs.research.skeleton import run_research
    from agent.llm import get_model
    from agent.tools.web_search import web_search

    if progress is None:
        def progress(*_args, **_kwargs):
            return None

    gate = get_model("gate").with_structured_output(SignalCard, strict=True)
    with SessionLocal() as session:
        structured = structured_for()
        search_fn = lambda t, attempt=1: web_search(_query(t, attempt), k=6)
        deps = SignalsDeps(build_targets(), structured, search_fn, gate)
        drafts = run_research(deps, progress=progress)
        progress("writing")
        progress("saving")
        n = persist_signals(session, drafts)
        session.commit()
    return {"signals_items": n}
