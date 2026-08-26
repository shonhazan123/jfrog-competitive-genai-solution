from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers import digests
from app.db.session import get_session

router = APIRouter(prefix="/digests", tags=["digests"])


@router.get("/exec/weekly")
def exec_weekly(
    session: Session = Depends(get_session),
    week_of: str | None = Query(None),
) -> dict:
    return digests.exec_weekly(session, week_of=week_of)
