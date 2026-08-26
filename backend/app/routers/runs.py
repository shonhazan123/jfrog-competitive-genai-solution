from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.controllers import runs
from app.db.session import get_session

router = APIRouter(prefix="/runs", tags=["runs"])

class RunRequest(BaseModel):
    kind: str
    reason: str | None = None

@router.post("", status_code=202)
def start_run(body: RunRequest) -> dict:
    return runs.start_run(body.kind, body.reason)

@router.post("/collect")
def collect() -> dict:
    return runs.trigger_collection()

@router.get("/status")
def status() -> dict:
    return runs.run_status()

@router.get("/latest")
def latest(session: Session = Depends(get_session)) -> dict:
    return runs.get_latest_run(session)
