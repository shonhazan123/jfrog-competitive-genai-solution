from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.db.session import SessionLocal
from app.models.capture import RawCapture
from app.models.registry import Entity, Source
from app.models.signal import Signal
from app.services.backfill import backfill_source, collect_snapshot_source
from agent.log import get_logger, step
from app.services.collection.apis.greenhouse import GreenhouseAdapter
from app.services.collection.apis.hackernews import HackerNewsAdapter
from app.services.collection.apis.lever import LeverAdapter
from app.services.collection.apis.osv import OsvAdapter
from app.services.collection.fetcher import Fetcher, StaticFetcher
from app.services.collection.fixture_fetcher import FixtureFetcher
from app.services.collection.feeds import parse_feed
from app.services.collection.robots import RobotsCache
from app.services.delivery.assembly import assemble
from app.services.delivery.email import send_digest
from app.services.scoring.materiality import score
from app.services.seeding import seed
from app.services.signals.novelty import is_new
from app.settings import settings

_ADAPTERS = {
    "osv": OsvAdapter(),
    "greenhouse": GreenhouseAdapter(),
    "lever": LeverAdapter(),
    "hn": HackerNewsAdapter(),
}
_WEEKDAYS = frozenset({"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"})
MANUAL_WINDOW_DAYS = 30
logger = get_logger("worker.jobs")


def _due(source: Source, now: datetime) -> bool:
    """A source is due when it has never been checked or its per-source interval has
    elapsed. Turns check_frequency_minutes from stored-but-ignored config into behaviour."""
    if source.last_checked_at is None:
        return True
    return now >= source.last_checked_at + timedelta(minutes=source.check_frequency_minutes)


def run_seed() -> None:
    with SessionLocal() as session:
        seed(session)


def run_backfill() -> dict[str, int]:
    """Replay archive history for every enabled snapshot-mode source.

    Change-detection backfill is benched for verdict-first daily runs. When enabled
    (``BACKFILL_ON_START=true`` or an explicit call), a missing offline fixture for
    one source must not abort replay for the rest."""
    totals = {"captures": 0, "claims": 0, "versions": 0, "skipped": 0}
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
            try:
                report = backfill_source(session, source, fetcher)
            except LookupError as exc:
                # Offline fixture replay: new snapshot sources may lack Wayback captures.
                logger.warning(
                    "backfill.skipped source=%s reason=%s",
                    source.key,
                    exc,
                )
                totals["skipped"] += 1
                continue
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


def _collect_source(session, source, fetcher, robots, now, force, report) -> None:
    if not force and not _due(source, now):
        report["skipped_not_due"] += 1
        return
    allowed = robots.allowed(source.url)
    source.robots_allowed = allowed
    source.last_checked_at = now
    source.check_count += 1
    if not allowed:
        report["skipped_robots"] += 1
        return

    # One malformed or unreachable source must never abort the whole daily run.
    try:
        if source.mode == "feed":
            result = fetcher.fetch(source.url, source.etag)
            if result.not_modified or not result.body:
                return
            if result.etag:
                source.etag = result.etag
            for entry in parse_feed(result.body, source.url):
                if (
                    force
                    and entry.published_at is not None
                    and entry.published_at < now - timedelta(days=MANUAL_WINDOW_DAYS)
                ):
                    continue
                if not is_new(session, source.id, entry.external_id):
                    continue
                text = entry.content_html or entry.summary_html or entry.title
                _store_capture(session, source, entry.external_id, text, entry.link)
                report["captures"] += 1
        elif source.mode == "api":
            adapter = _ADAPTERS.get(source.adapter or "")
            if adapter is None:
                return
            for record in adapter.collect(source, fetcher):
                if (
                    force
                    and record.occurred_at is not None
                    and record.occurred_at < now - timedelta(days=MANUAL_WINDOW_DAYS)
                ):
                    continue
                if not is_new(session, source.id, record.external_id):
                    continue
                _store_capture(session, source, record.external_id, record.body, record.url)
                report["captures"] += 1
        elif source.mode == "snapshot":
            if source.requires_js:
                return
            report["captures"] += collect_snapshot_source(session, source, fetcher)
    except Exception:
        report["errors"] += 1


def _run_collection_parallel(
    sources_or_groups,
    fetcher,
    *,
    robots,
    now,
    force,
    session_factory,
    max_workers=8,
) -> dict:
    """Fetch sources grouped by domain: domains run concurrently, one domain's
    sources run serially (respecting DomainRateLimiter). Each domain gets its own
    Session so no Session is shared across threads."""
    if isinstance(sources_or_groups, dict):
        groups = sources_or_groups
        n_sources = sum(len(ids) for ids in groups.values())
    else:
        groups: dict[str, list] = {}
        for source in sources_or_groups:
            groups.setdefault(urlparse(source.url).netloc, []).append(source.id)
        n_sources = len(sources_or_groups)

    totals = {
        "captures": 0,
        "skipped_robots": 0,
        "skipped_not_due": 0,
        "errors": 0,
        "sources": n_sources,
    }

    def _run_group(source_ids):
        report = {
            "captures": 0,
            "skipped_robots": 0,
            "skipped_not_due": 0,
            "errors": 0,
            "sources": 0,
        }
        with session_factory() as s:
            for sid in source_ids:
                source = s.query(Source).filter_by(id=sid).one()
                _collect_source(s, source, fetcher, robots, now, force, report)
            s.commit()
        return report

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for report in pool.map(_run_group, groups.values()):
            for key in ("captures", "skipped_robots", "skipped_not_due", "errors"):
                totals[key] += report[key]
    return totals


def run_collection(
    session: Session | None = None,
    fetcher: Fetcher | None = None,
    robots: RobotsCache | None = None,
    *,
    force: bool = False,
) -> dict:
    own_session = session is None
    if own_session:
        session = SessionLocal()
    if fetcher is None:
        fetcher = StaticFetcher()
    if robots is None:
        robots = RobotsCache()

    report = {
        "captures": 0, "skipped_robots": 0, "skipped_not_due": 0, "errors": 0, "sources": 0,
    }
    sources = session.query(Source).filter(
        Source.enabled.is_(True), Source.mode.in_(["feed", "api", "snapshot"])
    ).all()
    report["sources"] = len(sources)
    now = datetime.now(UTC)

    if own_session:
        groups: dict[str, list[int]] = {}
        for source in sources:
            groups.setdefault(urlparse(source.url).netloc, []).append(source.id)
        session.close()
        report = _run_collection_parallel(
            groups,
            fetcher,
            robots=robots,
            now=now,
            force=force,
            session_factory=SessionLocal,
        )
        report["sources"] = len(sources)
        step(logger, "collection.done", **report)
        return report

    for source in sources:
        _collect_source(session, source, fetcher, robots, now, force, report)

    step(logger, "collection.done", **report)
    return report


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


def today_name() -> str:
    return datetime.now(UTC).strftime("%a").upper()


def personas_due(cfg) -> list[str]:
    today = today_name()
    due: list[str] = []
    for persona, schedule in cfg.delivery.send_at.items():
        first_token = schedule.strip().split()[0].upper()
        if first_token in _WEEKDAYS:
            if first_token == today:
                due.append(persona)
        else:
            due.append(persona)
    return due


def _lazy_smtp(cfg) -> object:
    import os
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_cfg = cfg.delivery.smtp

    class _Smtp:
        def send(self, subject: str, html: str, to: list[str]) -> None:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_cfg.get("from_name", "JFrog CI")
            msg["To"] = ", ".join(to)
            msg.attach(MIMEText(html, "html"))
            with smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"]) as conn:
                if smtp_cfg.get("starttls"):
                    conn.starttls()
                user = os.environ.get("SMTP_USER")
                password = os.environ.get("SMTP_APP_PASSWORD")
                if user and password:
                    conn.login(user, password)
                conn.sendmail(msg["From"], to, msg.as_string())

    return _Smtp()


def run_digest(
    session: Session | None = None,
    smtp: object | None = None,
    personas: list[str] | None = None,
    cfg=None,
) -> dict:
    own_session = session is None
    if own_session:
        session = SessionLocal()
    cfg = cfg or load_config()
    personas = personas if personas is not None else ["sales", "product", "exec"]
    if smtp is None:
        smtp = _lazy_smtp(cfg)
    as_of = datetime.now(UTC)
    for persona in personas:
        digest = assemble(session, persona, cfg, as_of=as_of)
        send_digest(session, digest, smtp, cfg)
    if own_session:
        session.commit()
        session.close()
    return {"personas": personas, "sent": len(personas)}
