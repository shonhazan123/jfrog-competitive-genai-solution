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
