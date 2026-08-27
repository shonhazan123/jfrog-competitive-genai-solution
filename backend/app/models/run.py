from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

from app.settings import settings

RunStatus = Literal["running", "done", "failed"]


@dataclass
class Run:
    id: str
    stage_key: str
    current: int = 0
    total: int = 1
    status: RunStatus = "running"
    message: str = ""
    new_items: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None


_store: dict[str, Run] = {}
_current_run_id: str | None = None


@lru_cache(maxsize=1)
def load_run_stages() -> tuple[dict[str, str], ...]:
    path = Path(settings.config_dir) / "run_stages.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    stages = data["stages"]
    return tuple({"key": s["key"], "label": s["label"]} for s in stages)


def stage_label(stage_key: str) -> str:
    for stage in load_run_stages():
        if stage["key"] == stage_key:
            return stage["label"]
    return stage_key


def create_run() -> Run:
    global _current_run_id
    started = datetime.now(UTC)
    run_id = f"run_{started.strftime('%Y-%m-%dT%H:%M:%SZ')}_{uuid.uuid4().hex[:6]}"
    stages = load_run_stages()
    first_key = stages[0]["key"]
    run = Run(
        id=run_id,
        stage_key=first_key,
        current=0,
        total=len(stages),
        started_at=started,
    )
    _store[run_id] = run
    _current_run_id = run_id
    return run


def put_run(run: Run) -> None:
    global _current_run_id
    _store[run.id] = run
    _current_run_id = run.id


def get_run(run_id: str) -> Run | None:
    return _store.get(run_id)


def update_run(run_id: str, **kwargs) -> Run:
    run = _store[run_id]
    for key, value in kwargs.items():
        setattr(run, key, value)
    return run


def progress_body(run: Run) -> dict:
    return {
        "run_id": run.id,
        "status": run.status,
        "stage_label": stage_label(run.stage_key),
        "progress": {"current": run.current, "total": run.total},
        "new_items": run.new_items,
        "message": run.message,
    }
