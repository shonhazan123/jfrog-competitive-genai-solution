from sqlalchemy.orm import Session
from app.models.ledger import Claim
from agent.ports import ClaimRef

class DbClaimLookup:
    def __init__(self, session: Session) -> None:
        self._session = session

    def candidates(self, subject: str, tags: list[str], k: int = 5) -> list[ClaimRef]:
        from app.models.registry import Entity
        entity = self._session.query(Entity).filter_by(slug=subject).one_or_none()
        if entity is None:
            return []
        query = self._session.query(Claim).filter(Claim.subject_entity_id == entity.id)
        if tags:
            query = query.filter(Claim.capability_tags.contains(tags))
        rows = query.limit(k).all()
        return [ClaimRef(id=r.id, claim_text=r.claim_text, capability_tags=r.capability_tags) for r in rows]

    def jfrog_position(self, capability_tag: str) -> str | None:
        from app.models.registry import Entity
        jfrog = self._session.query(Entity).filter_by(slug="jfrog").one_or_none()
        if jfrog is None:
            return None
        claim = (
            self._session.query(Claim)
            .filter(Claim.subject_entity_id == jfrog.id, Claim.capability_tags.contains([capability_tag]))
            .first()
        )
        return claim.claim_text if claim else None
