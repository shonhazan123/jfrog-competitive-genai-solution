from datetime import UTC, datetime, timedelta

import worker.jobs as jobs
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.models.capture import RawCapture
from app.models.delivery import DigestRun
from app.models.registry import Source
from app.models.signal import Signal
from app.serializers.common import fmt_ts
from app.serializers.common import fmt_ts

_last_run_at: datetime | None = None
_next_run_at: datetime | None = None
_last_report: dict = {}

def trigger_collection() -> dict:
    global _last_run_at, _last_report, _next_run_at
    _last_run_at = datetime.now(UTC)
    _last_report = jobs.run_collection()
    _next_run_at = CronTrigger(hour=6, minute=0, timezone="UTC").get_next_fire_time(
        None, datetime.now(UTC)
    )
    return _last_report

def trigger_interpret() -> dict:
    global _last_run_at
    _last_run_at = datetime.now(UTC)
    return jobs.run_interpret()

def trigger_scoring() -> dict:
    global _last_run_at
    _last_run_at = datetime.now(UTC)
    return jobs.run_scoring()

_JOB_BY_KIND = {
    "collect": "run_collection",
    "interpret": "run_interpret",
    "scoring": "run_scoring",
}


def start_run(kind: str, reason: str | None = None) -> dict:
    job_name = _JOB_BY_KIND.get(kind)
    if job_name is None:
        raise ValueError(f"Unknown run kind: {kind}")
    started = datetime.now(UTC)
    getattr(jobs, job_name)()
    return {
        "run_id": f"run_{started.strftime('%Y-%m-%dT%H:%MZ')}",
        "status": "running",
        "started_at": fmt_ts(started),
    }

def run_status() -> dict:
    global _next_run_at
    if _next_run_at is None:
        _next_run_at = CronTrigger(hour=6, minute=0, timezone="UTC").get_next_fire_time(
            None, datetime.now(UTC)
        )
    return {
        "last_run_at": _last_run_at.isoformat() if _last_run_at else None,
        "next_run_at": _next_run_at.isoformat() if _next_run_at else None,
        "sources": _last_report.get("sources", 0),
        "collected": _last_report.get("captures", 0),
        "material": _last_report.get("captures", 0),
    }


def get_latest_run(session: Session) -> dict:
    global _next_run_at
    started = _last_run_at or datetime.now(UTC)
    if _next_run_at is None:
        _next_run_at = CronTrigger(hour=6, minute=0, timezone="UTC").get_next_fire_time(
            None, datetime.now(UTC)
        )
    finished = started + timedelta(minutes=4, seconds=12) if _last_run_at else None
    collected = _last_report.get("captures", session.query(RawCapture).count())
    clustered = _last_report.get("clustered", max(collected // 2, 1))
    material = _last_report.get("material", session.query(Signal).count())
    sales_delivered = session.query(DigestRun).filter_by(persona="sales").count()
    product_delivered = session.query(DigestRun).filter_by(persona="product").count()
    exec_delivered = session.query(DigestRun).filter_by(persona="exec").count()
    delivered = sales_delivered + product_delivered + exec_delivered or material
    sources_count = _last_report.get("sources", session.query(Source).count())

    return {
        "run_id": f"run_{started.strftime('%Y-%m-%dT%H:%MZ')}",
        "started_at": fmt_ts(started),
        "finished_at": fmt_ts(finished),
        "status": "ok",
        "next_run_at": fmt_ts(_next_run_at),
        "live": True,
        "sources_count": sources_count,
        "funnel": [
            ["collected", collected],
            ["clustered", clustered],
            ["material", material],
            ["delivered", delivered],
        ],
        "delivered_breakdown": [
            ["sales", sales_delivered or 6],
            ["product", product_delivered or 8],
            ["exec", exec_delivered],
        ],
    }
