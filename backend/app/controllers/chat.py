from sqlalchemy.orm import Session

from app.services.chat_service import answer_chat


def chat(session: Session, message: str, history: list[dict] | None = None,
         persona: str | None = None, conversation_id: str | None = None) -> dict:
    return answer_chat(session, message, history=history, persona=persona,
                       conversation_id=conversation_id)
