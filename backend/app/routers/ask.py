from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.controllers import ask
from app.db.session import get_session

router = APIRouter(prefix="/ask", tags=["ask"])


class AskRequest(BaseModel):
    question: str
    persona: str | None = None


@router.post("")
def post_ask(body: AskRequest, session: Session = Depends(get_session)) -> dict:
    return ask.ask(session, body.question, persona=body.persona)
