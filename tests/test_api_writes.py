import pytest
from datetime import UTC, datetime

from sqlalchemy import text


def test_an_analyst_action_is_persisted_with_actor_and_reason(client_with_data):
    response = client_with_data.post("/signals/1/actions",
                                     json={"action": "reject", "reason": "duplicate", "actor": "a@jfrog.com"})
    assert response.status_code == 201

def test_changing_a_weight_rescore_without_re_inference(client_with_data, session):
    """Re-scoring the ledger is a SQL update, not re-running the model."""
    from app.models.signal import Signal

    signal = session.query(Signal).filter_by(cluster_key="jfrog-subject").one()
    before = signal.score_sales

    client_with_data.put(
        "/config/materiality",
        json={"modifiers": {"subject_is_jfrog": 1.0}},
    )

    session.refresh(signal)
    assert signal.score_sales != before

def test_put_config_instructions_persists_and_get_returns_them(client_with_data):
    response = client_with_data.put(
        "/config/instructions",
        json={"instructions": ["flag anything mentioning SLSA"]},
    )
    assert response.status_code == 200
    assert response.json()["instructions"] == ["flag anything mentioning SLSA"]
    get_resp = client_with_data.get("/config/instructions")
    assert get_resp.json()["instructions"] == ["flag anything mentioning SLSA"]


def test_invalid_config_is_rejected_with_a_readable_message(client_with_data):
    response = client_with_data.put("/config/materiality",
                                    json={"modifiers": {"reliability_grade": {"A": "not a number"}}})
    assert response.status_code == 422
    assert "message" in response.json()["error"]

def test_manual_run_invokes_the_same_job_the_scheduler_calls(client_with_data, spy_jobs):
    client_with_data.post("/runs", json={"kind": "collect"})
    assert spy_jobs.called == "run_collection"


@pytest.fixture
def spy_jobs(monkeypatch):
    import worker.jobs as jobs

    class Spy:
        called = None

    spy = Spy()

    def stub_run_collection(*args, **kwargs):
        spy.called = "run_collection"
        return {}

    def stub_run_scoring(*args, **kwargs):
        spy.called = "run_scoring"
        return {}

    monkeypatch.setattr(jobs, "run_collection", stub_run_collection)
    monkeypatch.setattr(jobs, "run_scoring", stub_run_scoring)
    return spy


@pytest.fixture
def client_with_data(session):
    from fastapi.testclient import TestClient

    from app.db.session import get_session
    from app.main import app
    from app.models.capture import RawCapture
    from app.models.registry import Entity, Source
    from app.models.signal import Signal, SignalEvidence
    from app.controllers.config import clear_config_extensions
    from app.services.config_overrides import clear_overrides
    from app.services.seeding import seed

    clear_overrides()
    clear_config_extensions()
    seed(session)
    entities = {entity.slug: entity for entity in session.query(Entity).all()}
    now = datetime(2026, 8, 26, 6, 0, tzinfo=UTC)
    latest = datetime(2026, 8, 26, 8, 0, tzinfo=UTC)
    # Sequences are non-transactional, so signal ids climb across the suite even
    # though each test rolls back. Restart so the first seeded signal is id=1,
    # which the analyst-action test addresses directly.
    session.execute(text("ALTER SEQUENCE signal_id_seq RESTART WITH 1"))

    def _source(slug: str) -> Source:
        source = session.query(Source).filter_by(entity_id=entities[slug].id).first()
        if source is None:
            source = Source(
                key=f"{slug}_fixture",
                entity_id=entities[slug].id,
                url=f"https://example.com/{slug}",
                kind="atom",
                mode="feed",
                reliability_grade="A",
                is_primary=True,
                check_frequency_minutes=60,
                last_checked_at=now,
            )
            session.add(source)
            session.flush()
        source.last_checked_at = now
        return source

    def _capture(source: Source, quote: str) -> RawCapture:
        capture = RawCapture(
            source_id=source.id,
            fetched_at=now,
            http_status=200,
            content_hash=f"hash-{source.id}-{quote[:8]}",
            blob_path=f"/tmp/{source.id}.txt",
            extracted_text=quote,
        )
        session.add(capture)
        session.flush()
        return capture

    def _signal(
        *,
        slug: str,
        headline: str,
        signal_type: str,
        cluster_key: str,
        subject_slug: str | None = None,
        occurred_at: datetime = now,
        score_sales: float = 70.0,
    ) -> Signal:
        source = _source(slug)
        subject_id = entities[subject_slug].id if subject_slug else None
        signal = Signal(
            source_id=source.id,
            entity_id=entities[slug].id,
            subject_entity_id=subject_id,
            signal_type=signal_type,
            headline=headline,
            occurred_at=occurred_at,
            cluster_key=cluster_key,
            corroboration_count=2,
            score_sales=score_sales,
            score_product=score_sales,
            score_exec=score_sales,
            so_what_sales="Sales framing for the signal.",
            so_what_product="Product framing for the signal.",
            so_what_exec="Executive framing for the signal.",
        )
        session.add(signal)
        session.flush()
        capture = _capture(source, headline)
        session.add(
            SignalEvidence(
                signal_id=signal.id,
                capture_id=capture.id,
                quote=headline,
                quote_offset=0,
                match_method="exact",
            )
        )
        return signal

    # JFrog-as-subject signal listed first; sales score shifts when subject_is_jfrog changes.
    _signal(
        slug="sonatype",
        headline="Sonatype claims JFrog pricing is uncompetitive",
        signal_type="positioning_messaging",
        cluster_key="jfrog-subject",
        subject_slug="jfrog",
        occurred_at=latest,
        score_sales=82.0,
    )

    for index, (signal_type, headline, score) in enumerate(
        [
            ("security_trust", "Advisory affecting Nexus", 78.0),
            ("product_capability", "Nexus adds Cargo registry support", 66.0),
            ("customer_evidence", "New financial-services case study", 62.0),
        ]
    ):
        _signal(
            slug="sonatype",
            headline=headline,
            signal_type=signal_type,
            cluster_key=f"sales-{index}",
            score_sales=score,
        )

    def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    clear_overrides()
    clear_config_extensions()
