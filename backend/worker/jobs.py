from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.db.session import SessionLocal
from app.models.capture import RawCapture
from app.models.registry import Entity, Source
from app.models.signal import Signal, SignalEvidence
from app.services.agent_service import interpret_capture
from app.services.backfill import backfill_source
from app.services.collection.apis.osv import OsvAdapter
from app.services.collection.fetcher import Fetcher, StaticFetcher
from app.services.collection.fixture_fetcher import FixtureFetcher
from app.services.collection.feeds import parse_feed
from app.services.collection.robots import RobotsCache
from app.services.scoring.materiality import score
from app.services.seeding import seed
from app.services.signals.novelty import is_new
from app.settings import settings

_ADAPTERS = {"osv": OsvAdapter()}


def run_seed() -> None:
    with SessionLocal() as session:
        seed(session)


def run_backfill() -> dict[str, int]:
    """Replay archive history for every enabled snapshot-mode source."""
    totals = {"captures": 0, "claims": 0, "versions": 0}
    use_fixtures = settings.backfill_source == "fixtures"
    fetcher: Fetcher = (
        FixtureFetcher(settings.fixtures_dir) if use_fixtures else StaticFetcher()
    )
    robots = None if use_fixtures else RobotsCache()
    with SessionLocal() as session:
        sources = session.query(Source).filter_by(mode="snapshot", enabled=True).all()
        for source in sources:
            if use_fixtures:
                source.robots_allowed = True
            else:
                source.robots_allowed = robots.allowed(source.url)
            if not source.robots_allowed or source.requires_js:
                continue
            report = backfill_source(session, source, fetcher)
            totals["captures"] += report.captures
            totals["claims"] += report.claims_created
            totals["versions"] += report.versions_created
        session.commit()
    return totals


def _store_capture(
    session: Session, source: Source, external_id: str, text: str, url: str = "",
) -> RawCapture:
    capture = RawCapture(
        source_id=source.id,
        external_id=external_id,
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
        blob_path=url or source.url,
        extracted_text=text,
        provenance="live",
    )
    session.add(capture)
    return capture


def run_collection(
    session: Session | None = None,
    fetcher: Fetcher | None = None,
    robots: RobotsCache | None = None,
) -> dict:
    own_session = session is None
    if own_session:
        session = SessionLocal()
    if fetcher is None:
        fetcher = StaticFetcher()
    if robots is None:
        robots = RobotsCache()

    report = {"captures": 0, "skipped_robots": 0, "sources": 0}
    sources = session.query(Source).filter(Source.enabled.is_(True), Source.mode.in_(["feed", "api"])).all()
    report["sources"] = len(sources)

    for source in sources:
        allowed = robots.allowed(source.url)
        source.robots_allowed = allowed
        if not allowed:
            report["skipped_robots"] += 1
            continue

        if source.mode == "feed":
            result = fetcher.fetch(source.url, source.etag)
            if result.not_modified or not result.body:
                continue
            for entry in parse_feed(result.body, source.url):
                if not is_new(session, source.id, entry.external_id):
                    continue
                text = entry.content_html or entry.summary_html or entry.title
                _store_capture(session, source, entry.external_id, text, entry.link)
                report["captures"] += 1
        elif source.mode == "api":
            adapter = _ADAPTERS.get(source.adapter or "")
            if adapter is None:
                continue
            for record in adapter.collect(source, fetcher):
                if not is_new(session, source.id, record.external_id):
                    continue
                _store_capture(session, source, record.external_id, record.body, record.url)
                report["captures"] += 1

    if own_session:
        session.commit()
        session.close()
    return report


def run_interpret(session: Session | None = None, limit: int | None = None) -> dict:
    own_session = session is None
    if own_session:
        session = SessionLocal()
    interpreted = 0
    quarantined = 0
    interpreted_ids = {
        row[0] for row in session.query(SignalEvidence.capture_id).distinct().all()
    }
    if interpreted_ids:
        query = session.query(RawCapture).filter(RawCapture.id.notin_(interpreted_ids))
    else:
        query = session.query(RawCapture)
    captures = query.all()
    if limit is not None:
        captures = captures[:limit]
    for capture in captures:
        result = interpret_capture(capture.id, session=session)
        if result.status == "ok":
            interpreted += 1
        elif result.status == "quarantined":
            quarantined += 1
    if own_session:
        session.commit()
        session.close()
    return {"interpreted": interpreted, "quarantined": quarantined}


def run_scoring(session: Session | None = None) -> dict:
    own_session = session is None
    if own_session:
        session = SessionLocal()
    config = load_config()
    updated = 0
    for signal in session.query(Signal).all():
        source = session.query(Source).filter_by(id=signal.source_id).one()
        entity = session.query(Entity).filter_by(id=signal.entity_id).one()
        facets = {
            "signal_type": signal.signal_type,
            "subject_entity": None,
            "asserting_entity": entity.slug,
            "entity_tier": entity.tier,
            "reliability_grade": source.reliability_grade,
            "corroboration_count": signal.corroboration_count,
            "capability_tags": signal.capability_tags,
            "occurred_at": signal.occurred_at,
            "text": signal.headline,
        }
        signal.score_sales = score(facets, "sales", config).total
        signal.score_product = score(facets, "product", config).total
        signal.score_exec = score(facets, "exec", config).total
        updated += 1
    if own_session:
        session.commit()
        session.close()
    return {"scored": updated}
