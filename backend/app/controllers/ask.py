from sqlalchemy.orm import Session

from app.services.ask_service import answer_question


def ask(session: Session, question: str, persona: str | None = None) -> dict:
    return answer_question(session, question, persona=persona)
