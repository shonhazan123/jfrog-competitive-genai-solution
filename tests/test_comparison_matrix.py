from datetime import UTC, datetime

import pytest


@pytest.fixture
def comparison_seed(session):
    from app.services.seeding import seed

    seed(session)
    from app.models.registry import Entity

    return {e.slug: e for e in session.query(Entity).all()}


@pytest.fixture
def artifact_claim(session, comparison_seed):
    from app.models.capture import RawCapture
    from app.models.ledger import Claim, Evidence
    from app.models.registry import Source

    jfrog = comparison_seed["jfrog"]
    sonatype = comparison_seed["sonatype"]

    source = Source(
        key="comparison_matrix_fixture",
        entity_id=sonatype.id,
        url="https://example.com/nexus",
        kind="html_page",
        mode="snapshot",
        reliability_grade="B",
        is_primary=True,
        check_frequency_minutes=60,
        requires_js=False,
    )
    session.add(source)
    session.flush()

    capture = RawCapture(
        source_id=source.id,
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_hash="artifact-claim",
        blob_path="https://example.com/nexus",
        extracted_text="Nexus Repository supports universal formats.",
        provenance="live",
    )
    session.add(capture)
    session.flush()

    claim = Claim(
        subject_entity_id=jfrog.id,
        asserting_entity_id=sonatype.id,
        claim_text="Nexus Repository, mature artifact management.",
        claim_type="positioning",
        capability_tags=["artifact_management"],
        dimension="artifact_management",
        stance="moderate",
        status="active",
        reliability_grade="B",
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
    session.flush()
    return claim


def test_matrix_has_five_dimensions_and_five_competitors(session, comparison_seed):
    from app.services.comparison_matrix import build_comparison_matrix

    matrix = build_comparison_matrix(session)
    assert len(matrix["dimensions"]) == 5
    assert [d["key"] for d in matrix["dimensions"]] == [
        "artifact_management",
        "sca_sbom",
        "container_security",
        "cicd_integration",
        "developer_experience",
    ]
    assert {c["slug"] for c in matrix["competitors"]} == {
        "github",
        "sonatype",
        "snyk",
        "aqua",
        "checkmarx",
    }


def test_cell_with_claim_returns_stance_and_evidence(session, artifact_claim):
    from app.services.comparison_matrix import build_comparison_matrix

    matrix = build_comparison_matrix(session)
    artifact_col = next(d for d in matrix["dimensions"] if d["key"] == "artifact_management")
    sonatype_cell = next(c for c in artifact_col["cells"] if c["competitor"] == "sonatype")

    assert sonatype_cell["stance"] == "moderate"
    assert sonatype_cell["summary"] == "Nexus Repository, mature artifact management."
    assert sonatype_cell["jfrog_position"] == (
        "Artifactory — universal, 30+ package types, self-hosted + cloud."
    )
    assert sonatype_cell["evidence"]


def test_cell_without_claim_returns_none(session, comparison_seed):
    from app.services.comparison_matrix import build_comparison_matrix

    matrix = build_comparison_matrix(session)
    artifact_col = next(d for d in matrix["dimensions"] if d["key"] == "artifact_management")
    snyk_cell = next(c for c in artifact_col["cells"] if c["competitor"] == "snyk")

    assert snyk_cell["stance"] == "none"
    assert snyk_cell["summary"] == "No public claim on record."
    assert snyk_cell["evidence"] == []
