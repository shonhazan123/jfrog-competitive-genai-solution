from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.controllers import sources
from app.db.session import get_session

router = APIRouter(prefix="/sources", tags=["sources"])


class PatchSourceRequest(BaseModel):
    enabled: bool | None = None
    actor: str
    reason: str | None = None


@router.get("")
def list_sources(
    session: Session = Depends(get_session),
    entity: str | None = Query(None),
) -> dict:
    return sources.list_sources(session, entity=entity)


@router.patch("/{source_id}")
def patch_source(
    source_id: str,
    body: PatchSourceRequest,
    session: Session = Depends(get_session),
) -> dict:
    return sources.patch_source(
        session,
        source_id,
        enabled=body.enabled,
        actor=body.actor,
        reason=body.reason,
    )
