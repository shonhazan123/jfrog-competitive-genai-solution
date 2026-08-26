from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers import coverage
from app.db.session import get_session

router = APIRouter(prefix="/coverage", tags=["coverage"])


@router.get("")
def get_coverage(session: Session = Depends(get_session)) -> dict:
    return coverage.get_coverage_matrix(session)
