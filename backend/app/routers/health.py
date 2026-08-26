from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_session
from app.models.capture import RawCapture
from app.models.ledger import Claim, ClaimVersion

router = APIRouter()

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/stats")
def stats(session: Session = Depends(get_session)) -> dict[str, int]:
    return {
        "captures": session.query(RawCapture).count(),
        "claims": session.query(Claim).count(),
        "claim_versions": session.query(ClaimVersion).count(),
    }
