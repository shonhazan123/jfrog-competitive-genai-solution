from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers import email_preview
from app.db.session import get_session

router = APIRouter(prefix="/email", tags=["email"])


@router.get("/preview")
def preview(
    session: Session = Depends(get_session),
    persona: str = Query("sales"),
) -> dict:
    return email_preview.preview(session, persona=persona)
