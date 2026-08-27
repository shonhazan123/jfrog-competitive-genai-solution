import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
import app.models  # noqa: F401  -- register every table on Base.metadata
from app.models.base import Base

@pytest.fixture(scope="session")
def engine():
    with PostgresContainer("pgvector/pgvector:pg17", driver="psycopg") as pg:
        engine = create_engine(pg.get_connection_url())
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(engine)
        yield engine

@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    with sessionmaker(bind=connection)() as s:
        yield s
    transaction.rollback()
    connection.close()

@pytest.fixture
def sample_claim(session):
    from datetime import UTC, datetime
    from app.models.registry import Entity
    from app.models.ledger import Claim
    a = Entity(slug="jfrog", name="JFrog", kind="self", tier=1)
    b = Entity(slug="sonatype", name="Sonatype", kind="competitor", tier=1)
    session.add_all([a, b]); session.flush()
    claim = Claim(
        subject_entity_id=a.id, asserting_entity_id=b.id,
        claim_text="x", claim_type="pricing", capability_tags=[],
        reliability_grade="A", first_seen_at=datetime.now(UTC),
    )
    session.add(claim); session.flush()
    return claim

@pytest.fixture
def not_modified_fetcher():
    class _NotModified:
        def fetch(self, url, etag=None):
            class R: not_modified = True; body = b""; status = 304
            return R()
    return _NotModified()

@pytest.fixture
def seeded_source(session):
    from app.services.seeding import seed
    from app.models.registry import Source
    seed(session)
    return session.query(Source).filter_by(key="sonatype_compare_jfrog").one()

@pytest.fixture
def second_source(session):
    from app.models.registry import Source
    return session.query(Source).filter_by(key="harbor_releases").one()

@pytest.fixture
def seeded_api_source(session):
    from app.services.seeding import seed
    from app.models.registry import Source
    seed(session)
    return session.query(Source).filter_by(key="osv_nexus").one()
