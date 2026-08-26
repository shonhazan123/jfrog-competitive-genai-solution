import pytest

from app.config.loader import load_config
from app.models.registry import Entity, Source
from app.services.coverage import build_coverage_matrix


@pytest.fixture
def seeded_sources(session):
    sonatype = Entity(slug="sonatype", name="Sonatype", kind="competitor", tier=1)
    harbor = Entity(slug="harbor", name="Harbor", kind="competitor", tier=2)
    industry = Entity(slug="industry", name="Industry", kind="industry", tier=1)
    session.add_all([sonatype, harbor, industry])
    session.flush()

    session.add_all(
        [
            Source(
                key="sonatype_compare_jfrog",
                entity_id=sonatype.id,
                url="https://www.sonatype.com/compare/sonatype-nexus-versus-jfrog-artifactory",
                kind="html_page",
                mode="snapshot",
                reliability_grade="A",
                is_primary=True,
                check_frequency_minutes=1440,
            ),
            Source(
                key="sonatype_nexus_releases",
                entity_id=sonatype.id,
                url="https://github.com/sonatype/nexus-public/releases.atom",
                kind="atom",
                mode="feed",
                reliability_grade="A",
                is_primary=True,
                check_frequency_minutes=360,
            ),
            Source(
                key="harbor_releases",
                entity_id=harbor.id,
                url="https://github.com/goharbor/harbor/releases.atom",
                kind="atom",
                mode="feed",
                reliability_grade="A",
                is_primary=True,
                check_frequency_minutes=360,
            ),
        ]
    )
    session.flush()


@pytest.fixture
def blocked_source(session):
    entity = Entity(slug="gitlab", name="GitLab", kind="competitor", tier=2)
    session.add(entity)
    session.flush()

    signal_type = "talent_org"
    source = Source(
        key="gitlab_blocked_talent",
        entity_id=entity.id,
        url="https://example.com/gitlab/talent",
        kind="html_page",
        mode="snapshot",
        reliability_grade="B",
        is_primary=True,
        check_frequency_minutes=1440,
        robots_allowed=False,
        covers=[signal_type],
    )
    session.add(source)
    session.flush()

    class _BlockedSource:
        entity_slug = entity.slug
        covers = signal_type

    return _BlockedSource()


def test_matrix_has_a_row_per_entity_and_a_column_per_signal_type(session, seeded_sources):
    matrix = build_coverage_matrix(session, cfg=load_config())
    assert len(matrix.columns) == 9
    assert any(row.entity == "sonatype" for row in matrix.rows)


def test_a_cell_with_no_source_is_reported_as_a_gap(session, seeded_sources):
    matrix = build_coverage_matrix(session, cfg=load_config())
    row = next(r for r in matrix.rows if r.entity == "harbor")
    assert row.cells["pricing_packaging"].source_count == 0
    assert row.cells["pricing_packaging"].status == "gap"


def test_disabled_and_robots_blocked_sources_do_not_count_as_coverage(session, blocked_source):
    matrix = build_coverage_matrix(session, cfg=load_config())
    row = next(r for r in matrix.rows if r.entity == blocked_source.entity_slug)
    assert row.cells[blocked_source.covers].source_count == 0


def test_gap_total_is_reported_for_the_settings_header(session, seeded_sources):
    assert build_coverage_matrix(session, cfg=load_config()).gap_count > 0
