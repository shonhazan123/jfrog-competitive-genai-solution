from collections import Counter

import pytest

from app.config.loader import load_config
from app.models.delivery import Chunk
from app.services.retrieval.query import search

CFG = load_config()

SONATYPE_ID = 42
SONATYPE_SOURCE_IDS = [1001, 1002]
OTHER_ENTITY_ID = 99
OTHER_SOURCE_ID = 2001


@pytest.fixture
def indexed_chunks(session):
    chunks = [
        Chunk(
            record_type="claim",
            record_id=1,
            source_id=SONATYPE_SOURCE_IDS[0],
            entity_id=SONATYPE_ID,
            text="Sonatype detects malware in npm packages",
            prefix="malware threat",
            reliability_grade="A",
            content_hash="ret-malware-sonatype-1",
        ),
        Chunk(
            record_type="signal",
            record_id=2,
            source_id=SONATYPE_SOURCE_IDS[1],
            entity_id=SONATYPE_ID,
            text="malware campaign targeting cargo ecosystems",
            prefix="security malware",
            reliability_grade="B",
            content_hash="ret-malware-sonatype-2",
        ),
        Chunk(
            record_type="claim",
            record_id=3,
            source_id=OTHER_SOURCE_ID,
            entity_id=OTHER_ENTITY_ID,
            text="malware analysis blog post with extensive commentary",
            prefix="blog malware",
            reliability_grade="D",
            content_hash="ret-malware-other-1",
        ),
        Chunk(
            record_type="claim",
            record_id=10,
            source_id=SONATYPE_SOURCE_IDS[0],
            entity_id=SONATYPE_ID,
            text="Nexus adds Cargo registry support with full mirroring",
            prefix="cargo registry release",
            reliability_grade="A",
            content_hash="ret-cargo-1",
        ),
        Chunk(
            record_type="signal",
            record_id=11,
            source_id=SONATYPE_SOURCE_IDS[1],
            entity_id=SONATYPE_ID,
            text="cargo registry index updates for enterprise customers",
            prefix="registry cargo",
            reliability_grade="B",
            content_hash="ret-cargo-2",
        ),
        Chunk(
            record_type="claim",
            record_id=12,
            source_id=OTHER_SOURCE_ID,
            entity_id=OTHER_ENTITY_ID,
            text="cargo registry tutorial for beginners learning DevOps",
            prefix="registry cargo guide",
            reliability_grade="C",
            content_hash="ret-cargo-3",
        ),
        Chunk(
            record_type="claim",
            record_id=20,
            source_id=SONATYPE_SOURCE_IDS[0],
            entity_id=SONATYPE_ID,
            text="official Sonatype pricing page tier overview",
            prefix="pricing",
            reliability_grade="A",
            content_hash="ret-pricing-primary",
        ),
        Chunk(
            record_type="claim",
            record_id=21,
            source_id=OTHER_SOURCE_ID,
            entity_id=OTHER_ENTITY_ID,
            text="pricing pricing pricing competitive analysis blog pricing models pricing tiers pricing comparison",
            prefix="blog pricing",
            reliability_grade="D",
            content_hash="ret-pricing-blog",
        ),
        Chunk(
            record_type="claim",
            record_id=30,
            source_id=SONATYPE_SOURCE_IDS[0],
            entity_id=SONATYPE_ID,
            text="registry configuration part one for Nexus administrators",
            prefix="registry setup",
            reliability_grade="A",
            content_hash="ret-registry-30a",
        ),
        Chunk(
            record_type="claim",
            record_id=30,
            source_id=SONATYPE_SOURCE_IDS[0],
            entity_id=SONATYPE_ID,
            text="registry settings part two covering replication",
            prefix="registry replication",
            reliability_grade="A",
            content_hash="ret-registry-30b",
        ),
        Chunk(
            record_type="claim",
            record_id=30,
            source_id=SONATYPE_SOURCE_IDS[0],
            entity_id=SONATYPE_ID,
            text="registry advanced options for high availability",
            prefix="registry ha",
            reliability_grade="B",
            content_hash="ret-registry-30c",
        ),
        Chunk(
            record_type="signal",
            record_id=31,
            source_id=SONATYPE_SOURCE_IDS[1],
            entity_id=SONATYPE_ID,
            text="docker registry mirror setup guide",
            prefix="registry docker",
            reliability_grade="B",
            content_hash="ret-registry-31",
        ),
        Chunk(
            record_type="claim",
            record_id=32,
            source_id=OTHER_SOURCE_ID,
            entity_id=OTHER_ENTITY_ID,
            text="harbor registry deployment guide for kubernetes",
            prefix="registry harbor",
            reliability_grade="C",
            content_hash="ret-registry-32",
        ),
    ]
    session.add_all(chunks)
    session.flush()
    return chunks


def test_the_prefilter_is_mandatory_and_narrows_before_similarity(session, indexed_chunks):
    from app.services.retrieval.query import search

    hits = search(
        session,
        query="malware",
        preset="ask_ledger",
        filters={"entity_ids": [SONATYPE_ID]},
        cfg=CFG,
    )
    assert all(h.source_id in SONATYPE_SOURCE_IDS for h in hits)


def test_rrf_fuses_lexical_and_semantic_without_scale_tuning(session, indexed_chunks):
    hits = search(session, query="cargo registry", preset="ask_ledger", filters={}, cfg=CFG)
    assert hits and hits[0].score > hits[-1].score


def test_a_primary_grade_a_source_outranks_a_more_similar_blog(session, indexed_chunks):
    """The rerank encodes evidentiary value, not topical relevance."""
    hits = search(session, query="pricing", preset="ask_ledger", filters={}, cfg=CFG)
    assert hits[0].reliability_grade == "A"


def test_no_more_than_the_configured_chunks_come_from_one_document(session, indexed_chunks):
    hits = search(session, query="registry", preset="ask_ledger", filters={}, cfg=CFG)
    assert max(Counter(h.record_id for h in hits).values()) <= 2


def test_an_empty_prefilter_returns_nothing_and_never_widens(session, indexed_chunks):
    """A retriever that relaxes its own filter is how ungrounded answers happen."""
    hits = search(
        session,
        query="anything",
        preset="ask_ledger",
        filters={"entity_ids": [999999]},
        cfg=CFG,
    )
    assert hits == []
