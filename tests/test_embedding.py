import pytest

from app.models.delivery import Chunk
from app.services.ingestion.embedding import index_chunks, stale_chunk_count


@pytest.fixture
def fake_embedder():
    class _Fake:
        def __init__(self):
            self.calls = 0

        def embed(self, texts):
            self.calls += 1
            return [[0.0] * 1536 for _ in texts]

    return _Fake()


def test_upsert_is_idempotent_on_identical_content(session, fake_embedder):
    chunks = [
        {
            "text": "JFrog Artifactory supports Docker registry hosting.",
            "prefix": "[Product · Docker]",
            "section_path": ["Product", "Docker"],
            "token_count": 12,
        },
        {
            "text": "Maven repository proxying is available in all tiers.",
            "prefix": "[Product · Maven]",
            "section_path": ["Product", "Maven"],
            "token_count": 10,
        },
    ]
    index_chunks(session, chunks, record_type="claim", record_id=1, embedder=fake_embedder)
    first = session.query(Chunk).count()
    index_chunks(session, chunks, record_type="claim", record_id=1, embedder=fake_embedder)
    assert session.query(Chunk).count() == first
    assert fake_embedder.calls == 1


def test_changing_the_embed_model_marks_existing_chunks_stale(session, fake_embedder):
    chunks = [
        {
            "text": "Nexus adds Cargo registry support with full index mirroring.",
            "prefix": "[Release Notes · Cargo]",
            "section_path": ["Release Notes", "Cargo"],
            "token_count": 14,
        },
    ]
    index_chunks(
        session,
        chunks,
        record_type="claim",
        record_id=1,
        embedder=fake_embedder,
        embed_model="text-embedding-3-small",
    )
    assert stale_chunk_count(session, current_model="text-embedding-3-large") > 0


def test_chunk_metadata_is_stored_as_columns_not_json(session):
    """Metadata is filtered in SQL before the vector search; JSONB will not use btree."""
    for column in ("entity_id", "signal_type", "published_at", "reliability_grade"):
        assert column in Chunk.__table__.columns
