from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.controllers import signals
from app.db.session import get_session

router = APIRouter(prefix="/signals", tags=["signals"])


class AnalystActionRequest(BaseModel):
    action: str
    actor: str
    reason: str | None = None
    edit: dict | None = None
    relevance_adjustment: int | None = None


@router.get("")
def list_signals(
    session: Session = Depends(get_session),
    persona: str | None = Query(None),
    entity: str | None = Query(None),
    signal_type: str | None = Query(None),
    limit: int = Query(50),
) -> dict:
    return signals.list_signals(
        session,
        persona=persona,
        entity=entity,
        signal_type=signal_type,
        limit=limit,
    )


@router.post("/{signal_id}/actions", status_code=201)
def create_action(
    signal_id: int,
    body: AnalystActionRequest,
    session: Session = Depends(get_session),
) -> dict:
    return signals.create_action(
        session,
        signal_id,
        action=body.action,
        actor=body.actor,
        reason=body.reason,
        edit=body.edit,
        relevance_adjustment=body.relevance_adjustment,
    )
