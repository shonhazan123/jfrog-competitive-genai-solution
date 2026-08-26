from fastapi import APIRouter, Depends, Query
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
