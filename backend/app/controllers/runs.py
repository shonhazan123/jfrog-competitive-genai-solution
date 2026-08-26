from datetime import UTC, datetime

from apscheduler.triggers.cron import CronTrigger
from worker.jobs import run_collection, run_interpret, run_scoring

_last_run_at: datetime | None = None
_next_run_at: datetime | None = None
_last_report: dict = {}

def trigger_collection() -> dict:
    global _last_run_at, _last_report, _next_run_at
    _last_run_at = datetime.now(UTC)
    _last_report = run_collection()
    _next_run_at = CronTrigger(hour=6, minute=0, timezone="UTC").get_next_fire_time(
        None, datetime.now(UTC)
    )
    return _last_report

def trigger_interpret() -> dict:
    global _last_run_at
    _last_run_at = datetime.now(UTC)
    return run_interpret()

def trigger_scoring() -> dict:
    global _last_run_at
    _last_run_at = datetime.now(UTC)
    return run_scoring()

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
