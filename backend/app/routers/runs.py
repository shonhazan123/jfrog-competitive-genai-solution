from fastapi import APIRouter
from app.controllers import runs

router = APIRouter(prefix="/runs", tags=["runs"])

@router.post("/collect")
def collect() -> dict:
    return runs.trigger_collection()

@router.get("/status")
def status() -> dict:
    return runs.run_status()
