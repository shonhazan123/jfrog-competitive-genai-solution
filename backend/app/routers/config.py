from fastapi import APIRouter

from app.controllers import config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/materiality")
def get_materiality() -> dict:
    return config.get_materiality()


@router.get("/watchlist")
def get_watchlist() -> dict:
    return config.get_watchlist()
