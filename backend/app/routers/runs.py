from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.controllers import runs
from app.db.session import get_session

router = APIRouter(prefix="/runs", tags=["runs"])

class RunRequest(BaseModel):
    kind: str
    reason: str | None = None

@router.post("", status_code=202)
def start_run(body: RunRequest, background_tasks: BackgroundTasks) -> dict:
    if body.kind in {"industry", "signals", "comparison"}:
        return runs.start_surface_run(body.kind, background_tasks)
    return runs.start_run(body.kind, body.reason, background_tasks)

@router.post("/all", status_code=202)
def start_all_runs(background_tasks: BackgroundTasks) -> dict:
    return runs.start_all(background_tasks)

@router.post("/collect")
def collect() -> dict:
    return runs.trigger_collection()

@router.get("/status")
def status() -> dict:
    return runs.run_status()

@router.get("/latest")
def latest(session: Session = Depends(get_session)) -> dict:
    return runs.get_latest_run(session)

@router.get("/{run_id}")
def get_run_progress(run_id: str) -> dict:
    progress = runs.get_run_progress(run_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return progress
