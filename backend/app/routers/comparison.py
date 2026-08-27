from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers import comparison
from app.db.session import get_session

router = APIRouter(prefix="/comparison", tags=["comparison"])


@router.get("")
def list_comparison(
    session: Session = Depends(get_session),
    competitor: str = Query("sonatype"),
) -> dict:
    return comparison.list_comparison(session, competitor=competitor)


@router.get("/matrix")
def list_comparison_matrix(session: Session = Depends(get_session)) -> dict:
    return comparison.list_comparison_matrix(session)
