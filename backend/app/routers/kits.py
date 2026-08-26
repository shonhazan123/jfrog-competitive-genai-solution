from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services.kits import kit_to_dict, roll_up

router = APIRouter(prefix="/kits", tags=["kits"])


@router.get("")
def list_kits(session: Session = Depends(get_session)) -> dict:
    kits = roll_up(session)
    return {"items": [kit_to_dict(kit) for kit in kits], "total": len(kits), "cursor": None}
