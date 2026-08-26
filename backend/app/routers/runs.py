from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.controllers import runs
from app.db.session import get_session

router = APIRouter(prefix="/runs", tags=["runs"])

@router.post("/collect")
def collect() -> dict:
    return runs.trigger_collection()

@router.get("/status")
def status() -> dict:
    return runs.run_status()

@router.get("/latest")
def latest(session: Session = Depends(get_session)) -> dict:
    return runs.get_latest_run(session)
