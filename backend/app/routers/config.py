from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.controllers import config
from app.db.session import get_session
from app.services.config_overrides import ConfigValidationError

router = APIRouter(prefix="/config", tags=["config"])


class MaterialityUpdate(BaseModel):
    modifiers: dict | None = None
    weights: list[dict] | None = None
    actor: str | None = None


class WatchlistUpdate(BaseModel):
    terms: list[str]
    actor: str


@router.get("/materiality")
def get_materiality() -> dict:
    return config.get_materiality()


@router.get("/watchlist")
def get_watchlist() -> dict:
    return config.get_watchlist()


@router.put("/materiality")
def put_materiality(
    body: MaterialityUpdate,
    session: Session = Depends(get_session),
) -> dict:
    try:
        return config.update_materiality(session, body.model_dump(exclude_none=True))
    except ConfigValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": exc.code, "message": exc.message}},
        )


@router.put("/watchlist")
def put_watchlist(
    body: WatchlistUpdate,
    session: Session = Depends(get_session),
) -> dict:
    try:
        return config.update_watchlist(session, body.model_dump())
    except ConfigValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
