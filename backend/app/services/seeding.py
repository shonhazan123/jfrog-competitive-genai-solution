from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.config.loader import load_config
from app.models.registry import Entity, Source

@dataclass
class SeedReport:
    entities_created: int = 0
    sources_created: int = 0
    sources_updated: int = 0

def seed(session: Session) -> SeedReport:
    config, report = load_config(), SeedReport()

    by_slug: dict[str, Entity] = {e.slug: e for e in session.query(Entity).all()}
    for spec in config.entities:
        if spec.slug not in by_slug:
            entity = Entity(**spec.model_dump())
            session.add(entity)
            by_slug[spec.slug] = entity
            report.entities_created += 1
    session.flush()

    existing = {s.key: s for s in session.query(Source).all()}
    for spec in config.sources:
        payload = spec.model_dump(exclude={"entity"}) | {"entity_id": by_slug[spec.entity].id}
        if spec.key in existing:
            for field, value in payload.items():
                setattr(existing[spec.key], field, value)
            report.sources_updated += 1
        else:
            session.add(Source(**payload))
            report.sources_created += 1
    session.commit()
    return report
