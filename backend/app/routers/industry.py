from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.controllers import industry
from app.db.session import get_session

router = APIRouter(prefix="/industry", tags=["industry"])


@router.get("")
def list_industry(
    session: Session = Depends(get_session),
    limit: int = Query(50),
) -> dict:
    return industry.list_industry(session, limit=limit)


@router.get("/themes")
def list_themes(session: Session = Depends(get_session)) -> list[dict]:
    return industry.list_themes(session)


@router.get("/themes/{key}")
def theme_detail(key: str, session: Session = Depends(get_session)) -> dict:
    try:
        return industry.theme_detail(session, key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Theme not found") from None
