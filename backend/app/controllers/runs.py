from datetime import UTC, datetime

from worker.jobs import run_collection, run_interpret, run_scoring

_last_run_at: datetime | None = None
_next_run_at: datetime | None = None
_last_report: dict = {}

def trigger_collection() -> dict:
    global _last_run_at, _last_report
    _last_run_at = datetime.now(UTC)
    _last_report = run_collection()
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
    from worker.scheduler import build_scheduler
    global _next_run_at
    if _next_run_at is None:
        scheduler = build_scheduler()
        job = scheduler.get_job("collect")
        if job and job.next_run_time:
            _next_run_at = job.next_run_time
    return {
        "last_run_at": _last_run_at.isoformat() if _last_run_at else None,
        "next_run_at": _next_run_at.isoformat() if _next_run_at else None,
        "sources": _last_report.get("sources", 0),
        "collected": _last_report.get("captures", 0),
        "material": _last_report.get("captures", 0),
    }
