from datetime import UTC, datetime


def test_sanitize_text_strips_nul_and_control_chars_but_keeps_whitespace():
    from app.services.research.provenance import sanitize_text

    assert sanitize_text("Aqua\x00Trivy") == "AquaTrivy"
    assert sanitize_text("a\x07b\x1fc") == "abc"
    # tab / newline / carriage-return survive
    assert sanitize_text("line1\nline2\tend\r") == "line1\nline2\tend\r"
    # non-strings pass through untouched
    assert sanitize_text(None) is None


def test_record_finding_strips_nul_so_postgres_accepts_it(session):
    from app.models.capture import RawCapture
    from app.services.seeding import seed
    from app.services.research.provenance import record_finding

    seed(session)
    cap = record_finding(
        session,
        "signals",
        "https://x.com/a\x00b",
        "Aqua\x00Trivy path-traversal\x07 advisory",
    )
    session.flush()
    stored = session.query(RawCapture).filter_by(id=cap.id).one()
    assert "\x00" not in stored.extracted_text
    assert "\x00" not in stored.blob_path
    assert stored.extracted_text == "AquaTrivy path-traversal advisory"


def test_record_finding_creates_capture_under_synthetic_source(session):
    from app.models.capture import RawCapture
    from app.models.registry import Source
    from app.services.seeding import seed
    from app.services.research.provenance import record_finding, agent_source

    seed(session)
    cap = record_finding(session, "industry", "https://x.com/a", "malicious npm package found")
    session.flush()
    src = agent_source(session, "industry")
    assert cap.source_id == src.id
    assert cap.blob_path == "https://x.com/a"
    assert src.key == "industry_research"
    # idempotent: second call reuses the same source row
    assert agent_source(session, "industry").id == src.id


def test_index_finding_writes_a_chunk(session, monkeypatch):
    from app.models.delivery import Chunk
    from app.services.seeding import seed
    from app.services.research import provenance

    seed(session)

    class FakeEmbedder:
        def embed(self, texts):
            return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())
    n = provenance.index_finding(
        session, record_type="signal", record_id=1, text="malicious npm package",
        entity_id=None, signal_type="security_trust",
        published_at=datetime.now(UTC), reliability_grade="C",
    )
    session.flush()
    assert n == 1
    assert session.query(Chunk).filter_by(record_type="signal", record_id=1).count() == 1
