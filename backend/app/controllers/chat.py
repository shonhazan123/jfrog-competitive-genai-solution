from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.services.chat_service import answer_chat, answer_chat_stream


def chat(session: Session, message: str, history: list[dict] | None = None,
         persona: str | None = None, conversation_id: str | None = None) -> dict:
    return answer_chat(session, message, history=history, persona=persona,
                       conversation_id=conversation_id)


def chat_stream(session: Session, message: str, history: list[dict] | None = None,
                persona: str | None = None,
                conversation_id: str | None = None) -> Iterator[dict]:
    return answer_chat_stream(session, message, history=history, persona=persona,
                              conversation_id=conversation_id)
