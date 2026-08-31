from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.controllers import digests
from app.db.session import get_session

router = APIRouter(prefix="/digests", tags=["digests"])


class SendDemoRequest(BaseModel):
    to_email: str


@router.post("/send-demo")
def send_demo(
    body: SendDemoRequest,
    session: Session = Depends(get_session),
) -> dict:
    return digests.send_demo_digest(session, body.to_email)


@router.get("/exec/weekly")
def exec_weekly(
    session: Session = Depends(get_session),
    week_of: str | None = Query(None),
) -> dict:
    return digests.exec_weekly(session, week_of=week_of)


@router.get("/{persona}")
def persona_digest(
    persona: str,
    session: Session = Depends(get_session),
    date: str | None = Query(None),
) -> dict:
    return digests.persona_digest(session, persona, date=date)
