from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers import claims
from app.db.session import get_session

router = APIRouter(prefix="/claims", tags=["claims"])


@router.get("")
def list_claims(
    session: Session = Depends(get_session),
    subject: str = Query(...),
    asserter: str | None = Query(None),
) -> dict:
    return claims.list_claims(session, subject=subject, asserter=asserter)
