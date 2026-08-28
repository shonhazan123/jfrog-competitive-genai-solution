from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.controllers import chat as chat_controller
from app.db.session import get_session

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] = Field(default_factory=list)
    persona: str | None = None
    conversation_id: str | None = None


@router.post("")
def post_chat(body: ChatRequest, session: Session = Depends(get_session)) -> dict:
    history = [turn.model_dump() for turn in body.history]
    return chat_controller.chat(
        session, body.message, history=history,
        persona=body.persona, conversation_id=body.conversation_id,
    )
