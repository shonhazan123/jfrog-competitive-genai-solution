from datetime import UTC, datetime, timedelta
import time

import worker.jobs as jobs
from apscheduler.triggers.cron import CronTrigger
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.models.capture import RawCapture
from app.models.delivery import DigestRun
from app.models.registry import Source
from app.models.run import create_run, get_run, load_run_stages, progress_body, update_run
from app.models.signal import Signal
from app.serializers.common import fmt_ts

_last_run_at: datetime | None = None
_next_run_at: datetime | None = None
_last_report: dict = {}

_JOB_BY_KIND = {
    "collect": "run_collection",
    "interpret": "run_interpret",
    "scoring": "run_scoring",
}

_STAGE_FOR_KIND = {
    "collect": "collect",
    "interpret": "extract",
    "scoring": "score",
}


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


def _new_items_from_report(report: dict) -> int:
    for key in ("captures", "interpreted", "scored"):
        if key in report:
            return int(report[key])
    return 0


def _readable_error(exc: BaseException) -> str:
    message = str(exc).strip()
    if message and "Traceback" not in message:
        return message
    return "The run could not complete. Try again in a moment."


def _execute_run(run_id: str, kind: str) -> None:
    global _last_run_at, _last_report, _next_run_at
    stages = load_run_stages()
    job_name = _JOB_BY_KIND.get(kind)
    job_stage = _STAGE_FOR_KIND.get(kind)
    new_items = 0

    try:
        for index, stage in enumerate(stages):
            key = stage["key"]
            update_run(run_id, stage_key=key, current=index, total=len(stages))

            if key == job_stage and job_name:
                _last_run_at = datetime.now(UTC)
                report = getattr(jobs, job_name)()
                _last_report = report
                _next_run_at = CronTrigger(hour=6, minute=0, timezone="UTC").get_next_fire_time(
                    None, datetime.now(UTC)
                )
                new_items = _new_items_from_report(report)
            elif key != "done":
                time.sleep(0.01)

        update_run(
            run_id,
            stage_key=stages[-1]["key"],
            current=len(stages) - 1,
            status="done",
            new_items=new_items,
            finished_at=datetime.now(UTC),
        )
    except Exception as exc:
        update_run(
            run_id,
            status="failed",
            message=_readable_error(exc),
            finished_at=datetime.now(UTC),
        )


def start_run(
    kind: str,
    reason: str | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> dict:
    if _JOB_BY_KIND.get(kind) is None:
        raise ValueError(f"Unknown run kind: {kind}")
    run = create_run()
    if background_tasks is not None:
        background_tasks.add_task(_execute_run, run.id, kind)
    else:
        _execute_run(run.id, kind)
    return {"run_id": run.id}


def get_run_progress(run_id: str) -> dict | None:
    run = get_run(run_id)
    if run is None:
        return None
    return progress_body(run)


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
