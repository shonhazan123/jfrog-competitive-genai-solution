from datetime import UTC, datetime
import pytest
from app.config.loader import load_config
from app.services.verification import verify_quote

SOURCE = "Nexus 3.95 adds Cargo registry support with full index mirroring."

def good_extraction():
    return {"signal_type": "product_capability", "asserting_entity": "sonatype",
            "subject_entity": "sonatype", "mentions_jfrog": False, "headline": "Cargo support",
            "claims": [{"claim_text": "Nexus adds Cargo registry support",
                        "quote": "adds Cargo registry support with full index mirroring",
                        "claim_type": "capability", "capability_tags": ["package_format_support"]}]}

def bad_extraction():
    return {**good_extraction(),
            "claims": [{**good_extraction()["claims"][0], "quote": "will discontinue Artifactory"}]}

class FakeModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
    def invoke(self, _):
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response

@pytest.fixture
def capture_fixture(session, seeded_source):
    from app.models.capture import RawCapture
    capture = RawCapture(
        source_id=seeded_source.id,
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_hash="abc",
        blob_path="/tmp/x",
        extracted_text=SOURCE,
        provenance="live",
    )
    session.add(capture)
    session.flush()
    return capture

@pytest.fixture
def fake_deps(graph_deps):
    return graph_deps()

@pytest.fixture
def failing_deps(graph_deps):
    return graph_deps(extract=FakeModel([bad_extraction()]))

def test_successful_interpretation_persists_a_signal_with_evidence(session, capture_fixture, fake_deps):
    from app.services.agent_service import interpret_capture
    result = interpret_capture(capture_fixture.id, session=session, deps=fake_deps)
    from app.models.signal import Signal, SignalEvidence
    assert result.status == "ok"
    assert session.query(Signal).count() == 1
    assert session.query(SignalEvidence).count() >= 1

def test_quarantine_creates_a_queue_row_carrying_the_thread_id(session, capture_fixture, failing_deps):
    from app.services.agent_service import interpret_capture
    from app.models.signal import AnalystQueue
    result = interpret_capture(capture_fixture.id, session=session, deps=failing_deps)
    assert result.status == "quarantined"
    row = session.query(AnalystQueue).one()
    assert row.thread_id.startswith("interpret:")

def test_stored_evidence_quote_is_a_substring_of_the_capture(session, capture_fixture, fake_deps):
    from app.services.agent_service import interpret_capture
    from app.models.signal import SignalEvidence
    interpret_capture(capture_fixture.id, session=session, deps=fake_deps)
    evidence = session.query(SignalEvidence).first()
    assert evidence.quote in capture_fixture.extracted_text

def test_thread_id_includes_the_prompt_version_so_reanalysis_starts_fresh(session, capture_fixture, fake_deps):
    from app.services.agent_service import thread_id_for
    assert thread_id_for(capture_fixture.id, prompt_version=2) != thread_id_for(capture_fixture.id, prompt_version=1)

def test_zero_claim_capture_persists_no_signal(session, seeded_source, graph_deps):
    from app.models.capture import RawCapture
    from app.models.signal import Signal
    from app.services.agent_service import interpret_capture

    capture = RawCapture(
        source_id=seeded_source.id,
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_hash="empty-1",
        blob_path="/tmp/empty-1",
        extracted_text="Nothing competitive here at all.",
        provenance="test",
    )
    session.add(capture)
    session.flush()

    class _CtxBoom:
        def invoke(self, _):
            raise AssertionError("contextualize should be skipped on empty captures")

    deps = graph_deps(
        extract=FakeModel([{
            "signal_type": "product_capability",
            "asserting_entity": "sonatype",
            "subject_entity": "sonatype",
            "mentions_jfrog": False,
            "headline": "",
            "claims": [],
        }]),
        contextualize=_CtxBoom(),
    )

    before = session.query(Signal).count()
    result = interpret_capture(capture.id, session=session, deps=deps)
    assert result.status == "empty"
    assert session.query(Signal).count() == before

def test_self_guard_suppresses_self_subject_signal(session, seeded_source, graph_deps):
    from app.models.capture import RawCapture
    from app.models.signal import Signal
    from app.services.agent_service import interpret_capture

    text = "JFrog Artifactory lacks SBOM export while Nexus leads."
    capture = RawCapture(
        source_id=seeded_source.id,
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_hash="self-guard-1",
        blob_path="/tmp/self-guard-1",
        extracted_text=text,
        provenance="test",
    )
    session.add(capture)
    session.flush()

    extraction = {
        "signal_type": "product_capability",
        "asserting_entity": "sonatype",
        "subject_entity": "jfrog",
        "mentions_jfrog": True,
        "headline": "JFrog SBOM gap",
        "claims": [{
            "claim_text": "JFrog lacks SBOM export",
            "quote": "JFrog Artifactory lacks SBOM export",
            "claim_type": "capability",
            "capability_tags": ["sbom"],
        }],
    }
    deps = graph_deps(extract=FakeModel([extraction]))

    before = session.query(Signal).count()
    result = interpret_capture(capture.id, session=session, deps=deps)
    assert result.status == "empty"
    assert session.query(Signal).count() == before

def test_bridge_creates_dimensioned_claim_for_competitor(session, seeded_source, graph_deps):
    from app.models.capture import RawCapture
    from app.models.ledger import Claim, Evidence
    from app.models.registry import Entity
    from app.models.signal import Signal
    from app.services.agent_service import interpret_capture
    from app.services.comparison_matrix import build_comparison_matrix

    text = "Nexus adds SBOM export for all repositories."
    capture = RawCapture(
        source_id=seeded_source.id,
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_hash="bridge-1",
        blob_path="/tmp/bridge-1",
        extracted_text=text,
        provenance="test",
    )
    session.add(capture)
    session.flush()

    sonatype = session.query(Entity).filter_by(slug="sonatype").one()
    jfrog = session.query(Entity).filter_by(slug="jfrog").one()

    extraction = {
        "signal_type": "product_capability",
        "asserting_entity": "sonatype",
        "subject_entity": "sonatype",
        "mentions_jfrog": False,
        "headline": "SBOM export",
        "claims": [{
            "claim_text": "Nexus adds SBOM export",
            "quote": "Nexus adds SBOM export",
            "claim_type": "capability",
            "capability_tags": ["sbom"],
        }],
    }
    deps = graph_deps(extract=FakeModel([extraction]))

    result = interpret_capture(capture.id, session=session, deps=deps)
    assert result.status == "ok"
    assert session.query(Signal).count() == 1

    claim = session.query(Claim).filter_by(
        dimension="sbom",
        asserting_entity_id=sonatype.id,
        subject_entity_id=jfrog.id,
    ).one()
    assert claim.claim_type == "positioning"
    assert claim.reliability_grade == seeded_source.reliability_grade

    evidence = session.query(Evidence).filter_by(claim_id=claim.id).one()
    assert evidence.quote == "Nexus adds SBOM export"

    matrix = build_comparison_matrix(session)
    apptrust = next(c for c in matrix["components"] if c["key"] == "apptrust")
    sonatype_cell = next(cell for cell in apptrust["cells"] if cell["competitor"] == "sonatype")
    assert sonatype_cell["stance"] != "no_claim"

def test_bridge_skips_pricing_model_tag_not_a_dimension(session, seeded_source, graph_deps):
    from app.models.capture import RawCapture
    from app.models.ledger import Claim
    from app.models.signal import Signal
    from app.services.agent_service import interpret_capture

    text = "Nexus now offers consumption-based pricing for enterprise."
    capture = RawCapture(
        source_id=seeded_source.id,
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_hash="bridge-pricing-1",
        blob_path="/tmp/bridge-pricing-1",
        extracted_text=text,
        provenance="test",
    )
    session.add(capture)
    session.flush()

    extraction = {
        "signal_type": "product_capability",
        "asserting_entity": "sonatype",
        "subject_entity": "sonatype",
        "mentions_jfrog": False,
        "headline": "Pricing change",
        "claims": [{
            "claim_text": "Consumption-based pricing",
            "quote": "consumption-based pricing",
            "claim_type": "pricing",
            "capability_tags": ["pricing_model"],
        }],
    }
    deps = graph_deps(extract=FakeModel([extraction]))

    result = interpret_capture(capture.id, session=session, deps=deps)
    assert result.status == "ok"
    assert session.query(Signal).count() == 1
    assert session.query(Claim).filter_by(dimension="pricing_model").count() == 0
