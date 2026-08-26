from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.capture import RawCapture

def is_new(session: Session, source_id: int, external_id: str) -> bool:
    stmt = select(RawCapture.id).where(
        RawCapture.source_id == source_id, RawCapture.external_id == external_id
    ).limit(1)
    return session.execute(stmt).first() is None

def mark_seen(session: Session, source_id: int, external_id: str, capture_id: int | None) -> None:
    """Novelty is recorded on the capture itself; this is a no-op when the caller
    already created the capture with its external_id set."""
    if capture_id is None:
        session.add(RawCapture(
            source_id=source_id, external_id=external_id,
            fetched_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            http_status=200, content_hash="", blob_path="", extracted_text="",
            provenance="live",
        ))
    session.flush()
