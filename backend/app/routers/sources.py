from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers import sources
from app.db.session import get_session

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
def list_sources(
    session: Session = Depends(get_session),
    entity: str | None = Query(None),
) -> dict:
    return sources.list_sources(session, entity=entity)
