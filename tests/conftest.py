import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from app.models.base import Base

@pytest.fixture(scope="session")
def engine():
    with PostgresContainer("pgvector/pgvector:pg17", driver="psycopg") as pg:
        engine = create_engine(pg.get_connection_url())
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
