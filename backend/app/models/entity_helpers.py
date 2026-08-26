from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.registry import Entity

def entity_by_slug(session: Session, slug: str) -> Entity:
    return session.execute(select(Entity).where(Entity.slug == slug)).scalar_one()
