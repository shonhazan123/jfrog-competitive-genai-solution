from datetime import UTC, datetime

import pytest


REAL_URL = "https://www.sonatype.com/products/nexus-repository"
INTERNAL_URL = "internal://comparison_research"


@pytest.fixture
def web_search_capture(session):
    from app.models.capture import RawCapture
    from app.models.ledger import Claim, Evidence
    from app.models.registry import Source
    from app.models.signal import Signal, SignalEvidence
    from app.services.research.provenance import record_finding
    from app.services.seeding import seed

    seed(session)
    from app.models.registry import Entity

    entities = {e.slug: e for e in session.query(Entity).all()}
    jfrog = entities["jfrog"]
    sonatype = entities["sonatype"]
    industry = entities["industry"]

    capture = record_finding(
        session,
        "comparison",
        REAL_URL,
        "Nexus Repository supports universal formats.",
    )
    comparison_source = session.query(Source).filter_by(key="comparison_research").one()

    claim = Claim(
        subject_entity_id=jfrog.id,
        asserting_entity_id=sonatype.id,
        claim_text="Nexus Repository, mature artifact management.",
        claim_type="positioning",
        capability_tags=["artifact_management"],
        dimension="artifact_management",
        stance="moderate",
        status="active",
        reliability_grade="C",
        first_seen_at=datetime.now(UTC),
        last_confirmed_at=datetime.now(UTC),
    )
    session.add(claim)
    session.flush()
    session.add(
        Evidence(
            claim_id=claim.id,
            capture_id=capture.id,
            quote="Nexus Repository",
            quote_offset=0,
        )
    )

    industry_capture = record_finding(
        session,
        "industry",
        "https://digital-strategy.ec.europa.eu/cra",
        "EU CRA requires SBOM.",
    )
    industry_source = session.query(Source).filter_by(key="industry_research").one()
    industry_signal = Signal(
        source_id=industry_source.id,
        entity_id=industry.id,
        signal_type="market_regulatory",
        theme_key="regulation_compliance",
        headline="EU CRA SBOM mandate",
        occurred_at=datetime.now(UTC),
        cluster_key="industry-regulation",
        score_sales=50.0,
        score_product=50.0,
        score_exec=50.0,
        so_what_product="Regulatory framing.",
    )
    session.add(industry_signal)
    session.flush()
    session.add(
        SignalEvidence(
            signal_id=industry_signal.id,
            capture_id=industry_capture.id,
            quote="EU CRA requires SBOM.",
            quote_offset=0,
            match_method="synthesis",
        )
    )
    session.flush()

    return {
        "capture": capture,
        "comparison_source": comparison_source,
        "claim": claim,
        "industry_signal": industry_signal,
        "industry_capture": industry_capture,
    }


def test_evidence_from_capture_uses_real_url_for_web_search(session, web_search_capture):
    from app.serializers.common import evidence_from_capture

    row = web_search_capture
    evidence = evidence_from_capture(
        quote="Nexus Repository",
        capture=row["capture"],
        source=row["comparison_source"],
        reliability_grade="C",
        credibility_score=3,
    )

    assert evidence["source_url"] == REAL_URL
    assert evidence["source_url"].startswith("https://")
    assert INTERNAL_URL not in evidence["source_url"]
    assert evidence["citation"]["source_url"] == REAL_URL
    assert evidence["source_name"] == "sonatype.com"


def test_comparison_matrix_evidence_links_to_real_url(session, web_search_capture):
    from app.services.comparison_matrix import build_comparison_matrix

    matrix = build_comparison_matrix(session)
    artifact_col = next(d for d in matrix["dimensions"] if d["key"] == "artifact_management")
    sonatype_cell = next(c for c in artifact_col["cells"] if c["competitor"] == "sonatype")

    assert sonatype_cell["evidence"]
    url = sonatype_cell["evidence"][0]["source_url"]
    assert url == REAL_URL
    assert not url.startswith("internal://")


def test_signal_evidence_links_to_real_url(session, web_search_capture):
    from app.controllers.signals import _signal_evidence

    evidence = _signal_evidence(session, web_search_capture["industry_signal"])
    assert evidence
    url = evidence[0]["source_url"]
    assert url == "https://digital-strategy.ec.europa.eu/cra"
    assert not url.startswith("internal://")
    assert evidence[0]["citation"]["source_url"] == url
    assert evidence[0]["source_name"] == "digital-strategy.ec.europa.eu"


def test_industry_theme_item_links_to_real_url(session, web_search_capture):
    from app.services.industry_themes import build_industry_item

    item = build_industry_item(session, web_search_capture["industry_signal"])
    url = item["evidence"]["source_url"]
    assert url == "https://digital-strategy.ec.europa.eu/cra"
    assert not url.startswith("internal://")
