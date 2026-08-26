from app.services.seeding import seed

def test_seed_is_idempotent(session):
    first = seed(session)
    second = seed(session)
    assert first.entities_created > 0
    assert second.entities_created == 0
    assert second.sources_created == 0

def test_seed_links_sources_to_entities(session):
    from app.models.registry import Source, Entity
    seed(session)
    source = session.query(Source).filter_by(key="sonatype_compare_jfrog").one()
    entity = session.get(Entity, source.entity_id)
    assert entity.slug == "sonatype"
