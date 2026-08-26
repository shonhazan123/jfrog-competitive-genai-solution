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

@pytest.fixture
def graph_deps():
    from langgraph.checkpoint.memory import MemorySaver
    from app.config.loader import load_config
    from app.services.verification import verify_quote

    config = load_config()

    def _factory(extract=None, contextualize=None):
        class Deps:
            max_input_chars = 50_000
            max_repairs = 2
            verification_config = config.verification
            verify_quote = staticmethod(verify_quote)
            checkpointer = MemorySaver()
            use_interrupt = False
            extract_model = extract
            contextualize_model = contextualize
            @staticmethod
            def prompt(name):
                return "CONTENT:\n{content}"
            @staticmethod
            def crossref(_state):
                return []

        if Deps.extract_model is None:
            Deps.extract_model = _default_extract_model()
        if Deps.contextualize_model is None:
            Deps.contextualize_model = _default_contextualize_model()
        return Deps()

    return _factory

def _default_extract_model():
    class M:
        def invoke(self, _):
            return {
                "signal_type": "product_capability", "asserting_entity": "sonatype",
                "subject_entity": "sonatype", "mentions_jfrog": False, "headline": "Cargo support",
                "claims": [{"claim_text": "Nexus adds Cargo registry support",
                            "quote": "adds Cargo registry support with full index mirroring",
                            "claim_type": "capability", "capability_tags": ["package_format_support"]}],
            }
    return M()

def _default_contextualize_model():
    class M:
        def invoke(self, _):
            return {
                "so_what_sales": "s", "so_what_product": "p", "so_what_exec": "e",
                "relevance_adjustment": 0.0, "adjustment_reason": "",
            }
    return M()
