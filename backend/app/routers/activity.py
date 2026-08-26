from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers import activity
from app.db.session import get_session

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/since-last-visit")
def since_last_visit(
    session: Session = Depends(get_session),
    actor: str = "default",
) -> dict:
    return activity.since_last_visit(session, actor=actor)
