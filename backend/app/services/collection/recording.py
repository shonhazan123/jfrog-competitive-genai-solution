from datetime import UTC, datetime
from sqlalchemy.orm import Session
from app.models.registry import Source

def record_check(session: Session, source: Source, status: int) -> None:
    """A check is a fetch attempt, including a 304. Captures are not checks —
    conditional GET means an unchanged page produces no capture, so counting
    captures would understate how often we looked."""
    source.check_count = (source.check_count or 0) + 1
    source.last_checked_at = datetime.now(UTC)
    session.flush()
