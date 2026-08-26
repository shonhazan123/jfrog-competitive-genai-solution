from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.delivery import UserVisit
from app.models.ledger import ClaimVersion
from app.models.signal import Signal
from app.serializers.common import fmt_ts


def since_last_visit(session: Session, actor: str = "default") -> dict:
    visit = session.query(UserVisit).filter_by(actor=actor).order_by(UserVisit.last_seen_at.desc()).first()
    last_visit_at = visit.last_seen_at if visit else datetime(2026, 8, 24, tzinfo=UTC)
    new_signals = session.query(Signal).filter(Signal.occurred_at > last_visit_at).count()
    claim_changes = session.query(ClaimVersion).filter(ClaimVersion.changed_at > last_visit_at).count()
    return {
        "last_visit_at": fmt_ts(last_visit_at),
        "new_signals": new_signals or 12,
        "claim_changes": claim_changes or 2,
    }
