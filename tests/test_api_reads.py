import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "client" / "src" / "fixtures"

CASES = [
    ("/runs/latest", "run_status.json"),
    ("/activity/since-last-visit", "since_last_visit.json"),
    ("/signals?persona=sales", "signals_sales.json"),
    ("/digests/exec/weekly", "digest_exec_weekly.json"),
    ("/comparison?competitor=sonatype", "comparison_sonatype.json"),
    ("/claims?subject=jfrog", "claims_about_jfrog.json"),
    ("/industry", "industry_feed.json"),
    ("/sources", "sources.json"),
    ("/config/materiality", "materiality_weights.json"),
    ("/config/watchlist", "watchlist.json"),
    ("/coverage", "coverage_matrix.json"),
    ("/email/preview?persona=sales", "email_preview.json"),
]


@pytest.mark.parametrize("path,fixture", CASES)
def test_response_shape_matches_the_contract_fixture(client_with_data, path, fixture):
    expected = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    actual = client_with_data.get(path).json()
    assert _shape(actual) == _shape(expected), f"{path} diverges from {fixture}"


def _shape(value):
    """Compare structure and types, not values."""
    if isinstance(value, dict):
        return {k: _shape(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_shape(value[0])] if value else []
    return type(value).__name__


def test_list_endpoints_use_the_items_total_cursor_envelope(client_with_data):
    body = client_with_data.get("/signals?persona=product").json()
    assert {"items", "total", "cursor"} <= set(body)


def test_timestamps_carry_a_utc_offset(client_with_data):
    body = client_with_data.get("/runs/latest").json()
    assert body["started_at"].endswith("+00:00")


@pytest.fixture
def client_with_data(session):
    from fastapi.testclient import TestClient

    from app.controllers import runs as runs_controller
    from app.db.session import get_session
    from app.main import app
    from app.models.capture import RawCapture
    from app.models.delivery import DigestRun, UserVisit
    from app.models.ledger import Claim, ClaimVersion, Evidence
    from app.models.registry import Entity, Source
    from app.models.signal import Signal, SignalEvidence
    from app.services.seeding import seed

    seed(session)
    entities = {entity.slug: entity for entity in session.query(Entity).all()}
    now = datetime(2026, 8, 26, 6, 0, tzinfo=UTC)
    # Seeded sources carry no check timestamp; the contract shows a real one, so
    # stamp them all (the first row must have a non-null last_checked).
    for seeded in session.query(Source).all():
        seeded.last_checked_at = now
    session.flush()

    runs_controller._last_run_at = now
    runs_controller._next_run_at = datetime(2026, 8, 27, 6, 0, tzinfo=UTC)
    runs_controller._last_report = {
        "sources": 23,
        "captures": 94,
        "clustered": 41,
        "material": 11,
    }

    session.add(
        UserVisit(actor="default", last_seen_at=datetime(2026, 8, 24, tzinfo=UTC))
    )
    session.add_all(
        [
            DigestRun(persona="sales", generated_at=now, item_count=6),
            DigestRun(persona="product", generated_at=now, item_count=8),
        ]
    )

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
        handling: str | None = None,
        score_sales: float = 70.0,
        score_product: float | None = None,
        occurred_at: datetime = now,
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
            score_product=score_product if score_product is not None else score_sales,
            score_exec=score_sales,
            so_what_sales="Sales framing for the signal.",
            so_what_product="Product framing for the signal.",
            so_what_exec="Executive framing for the signal.",
            handling=handling,
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

    # (type, headline, handling, score_sales, score_product, subject_slug, hours_offset)
    # The caution security signal tops the sales view (latest + highest sales
    # score) and carries a JFrog subject; a capability signal tops the product
    # view via its product score, so the two personas surface different leads.
    sales_types = [
        ("security_trust", "Advisory affecting Nexus", "caution", 78.0, 78.0, "jfrog", 2),
        ("product_capability", "Nexus adds Cargo registry support", None, 66.0, 90.0, None, 0),
        ("customer_evidence", "New financial-services case study", None, 62.0, 62.0, None, 0),
        ("partnership_ecosystem", "Cloud marketplace listing", None, 51.0, 51.0, None, 0),
        ("product_capability", "Nexus deprecates Java 11", None, 47.0, 47.0, None, 0),
        ("market_regulatory", "EU CRA reporting obligations dated", None, 44.0, 44.0, None, 0),
    ]
    for index, (
        signal_type,
        headline,
        handling,
        score,
        score_product,
        subject_slug,
        hours_offset,
    ) in enumerate(sales_types):
        _signal(
            slug="sonatype",
            headline=headline,
            signal_type=signal_type,
            cluster_key=f"sales-{index}",
            handling=handling,
            score_sales=score,
            score_product=score_product,
            subject_slug=subject_slug,
            occurred_at=now + timedelta(hours=hours_offset),
        )

    industry_source = _source("industry")
    for index, signal_type in enumerate(
        ["market_regulatory", "security_trust", "partnership_ecosystem"]
    ):
        signal = Signal(
            source_id=industry_source.id,
            entity_id=entities["industry"].id,
            signal_type=signal_type,
            headline=f"Industry signal {index}",
            occurred_at=now,
            cluster_key=f"industry-{index}",
            score_sales=50.0,
            score_product=50.0,
            score_exec=50.0,
            so_what_product="Industry body copy.",
        )
        session.add(signal)
        session.flush()
        capture = _capture(industry_source, signal.headline)
        session.add(
            SignalEvidence(
                signal_id=signal.id,
                capture_id=capture.id,
                quote=signal.headline,
                quote_offset=0,
                match_method="exact",
            )
        )

    jfrog = entities["jfrog"]
    sonatype = entities["sonatype"]
    compare_source = _source("sonatype")
    claim_specs = [
        ("malware_detection", "JFrog malware detection is very limited, not proactive", "positioning"),
        ("sbom", "JFrog SBOM support is export only", "capability"),
        ("pricing_model", "Beware hidden costs with JFrog Artifactory", "pricing"),
        ("package_format_support", "Added Cargo registry support", "capability"),
        ("model_registry", "Firewall scans Hugging Face model artifacts", "capability"),
        ("deployment_model", "Deploy Nexus self-hosted or managed cloud", "capability"),
    ]
    for dimension, text, claim_type in claim_specs:
        claim = Claim(
            subject_entity_id=jfrog.id,
            asserting_entity_id=sonatype.id,
            claim_text=text,
            claim_type=claim_type,
            capability_tags=[dimension],
            dimension=dimension,
            reliability_grade="A",
            first_seen_at=datetime(2024, 1, 1, tzinfo=UTC),
            last_confirmed_at=now,
        )
        session.add(claim)
        session.flush()
        capture = _capture(compare_source, text)
        session.add(
            Evidence(
                claim_id=claim.id,
                capture_id=capture.id,
                quote=text,
                quote_offset=0,
            )
        )
        session.add(
            ClaimVersion(
                claim_id=claim.id,
                old_text="Limited" if dimension == "malware_detection" else None,
                new_text=text,
                change_kind="substantive" if dimension == "malware_detection" else "new",
                changed_at=now,
            )
        )

    blocked = Source(
        key="sonatype_devportal",
        entity_id=sonatype.id,
        url="https://example.com/devportal",
        kind="html_page",
        mode="snapshot",
        reliability_grade="C",
        is_primary=False,
        check_frequency_minutes=1440,
        robots_allowed=False,
        enabled=False,
        requires_js=True,
    )
    session.add(blocked)
    session.flush()

    def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
