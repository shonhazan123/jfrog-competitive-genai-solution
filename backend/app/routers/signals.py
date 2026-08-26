from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers import signals
from app.db.session import get_session

router = APIRouter(prefix="/signals", tags=["signals"])


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
