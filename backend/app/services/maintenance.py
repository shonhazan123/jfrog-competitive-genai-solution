from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.delivery import Chunk
from app.models.ledger import Claim, ClaimVersion, Evidence
from app.models.signal import AnalystAction, AnalystQueue, Signal, SignalEvidence


def reset_findings(session: Session) -> dict[str, int]:
    """Delete every row produced by the interpret/agent pipeline, keeping the
    registry (entities, sources) and raw captures. Children before parents so
    foreign keys never block the delete."""
    counts: dict[str, int] = {}
    for model in (
        Chunk,            # vector index rows
        SignalEvidence,   # signal children
        Evidence,         # claim children
        ClaimVersion,     # claim children
        Signal,
        Claim,
        AnalystQueue,
        AnalystAction,
    ):
        counts[model.__tablename__] = session.query(model).delete()
    session.flush()
    return counts


if __name__ == "__main__":  # pragma: no cover - operational entrypoint
    from app.db.session import SessionLocal

    with SessionLocal() as s:
        report = reset_findings(s)
        s.commit()
        print("reset_findings:", report)
