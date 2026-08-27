from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers import today
from app.db.session import get_session

router = APIRouter(prefix="/today", tags=["today"])


@router.get("")
def get_today(session: Session = Depends(get_session)) -> dict:
    return today.get_today(session)
