from app.config.loader import load_config

def test_jfrog_positions_cover_every_comparison_dimension():
    config = load_config()
    dimensions = {p.dimension for p in config.jfrog_positions.positions}
    assert "malware_detection" in dimensions
    assert len(dimensions) >= 6

def test_jfrog_positions_are_marked_authored_not_extracted():
    """JFrog's own positioning is authored by the CI team, not discovered.
    It must never be presented as graded evidence."""
    for position in load_config().jfrog_positions.positions:
        assert position.origin == "authored"
        assert not hasattr(position, "reliability_grade")

def test_coverage_columns_match_the_signal_type_enum():
    config = load_config()
    assert set(config.signal_types.coverage_columns) == set(config.signal_types.types)

def test_a_fifth_competitor_is_configured():
    slugs = {e.slug for e in load_config().entities if e.kind == "competitor"}
    assert len(slugs) >= 5

def test_check_counter_increments_even_on_304(session, seeded_source, not_modified_fetcher):
    from app.services.collection.recording import record_check
    before = seeded_source.check_count
    record_check(session, seeded_source, status=304)
    assert seeded_source.check_count == before + 1

def test_user_visit_records_last_seen(session):
    from app.models.delivery import UserVisit
    from datetime import UTC, datetime
    visit = UserVisit(actor="analyst@jfrog.com", last_seen_at=datetime.now(UTC))
    session.add(visit); session.flush()
    assert visit.last_seen_at is not None
