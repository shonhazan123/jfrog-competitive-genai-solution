import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
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


@router.post("/stream")
def post_chat_stream(body: ChatRequest, session: Session = Depends(get_session)) -> StreamingResponse:
    history = [turn.model_dump() for turn in body.history]

    def event_source():
        events = chat_controller.chat_stream(
            session, body.message, history=history,
            persona=body.persona, conversation_id=body.conversation_id,
        )
        for event in events:
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
