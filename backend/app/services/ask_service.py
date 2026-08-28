from __future__ import annotations

from sqlalchemy.orm import Session

from agent.log import get_logger, step
from app.services.chat_service import answer_chat

logger = get_logger("app.ask_service")


def answer_question(session: Session, question: str, persona: str | None = None) -> dict:
    """POST /ask, reimplemented on the chat path with no conversation window.

    Maps the chat result back to the legacy /ask response shape so existing
    consumers keep working during the transition.
    """
    step(logger, "ask.request.start", question=question, persona=persona)
    result = answer_chat(session, question, history=[], persona=persona)
    grounded = bool(result.get("grounded"))
    reason = result.get("reason")
    answer = result.get("answer") or (reason or "")
    evidence = result.get("sources", []) if grounded else []
    step(logger, "ask.request.done", question=question, grounded=grounded,
         evidence=len(evidence))
    return {
        "question": question,
        "persona": persona,
        "grounded": grounded,
        "answer": answer,
        "evidence": evidence,
        "refusal_reason": None if grounded else reason,
        "nearby_evidence": result.get("nearby_evidence", []),
    }
