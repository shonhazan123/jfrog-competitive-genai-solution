from datetime import UTC, datetime

import pytest

from app.models.delivery import Chunk
from app.models.registry import Entity, Source


@pytest.fixture
def seeded_corpus(session):
    jf = Entity(slug="jfrog", name="JFrog", kind="self", tier=1)
    sona = Entity(slug="sonatype", name="Sonatype", kind="competitor", tier=1)
    session.add_all([jf, sona])
    session.flush()
    src = Source(
        key="sonatype_pricing", entity_id=sona.id, url="https://sonatype.com/pricing",
        kind="html_page", mode="snapshot", reliability_grade="A", is_primary=True,
        check_frequency_minutes=1440, last_checked_at=datetime.now(UTC),
    )
    session.add(src)
    session.flush()
    session.add_all([
        Chunk(record_type="claim", record_id=1, source_id=src.id, entity_id=sona.id,
              text="Sonatype Nexus Repository is offered in tiered pricing plans.",
              prefix="pricing", reliability_grade="A", content_hash="chat-sona-pricing-1"),
        Chunk(record_type="signal", record_id=2, source_id=src.id, entity_id=sona.id,
              text="Nexus enterprise tier adds SSO and support SLAs.",
              prefix="pricing enterprise", reliability_grade="B", content_hash="chat-sona-pricing-2"),
    ])
    session.flush()
    return {"jfrog": jf, "sonatype": sona, "source": src}


class _CannedPlan:
    def __init__(self, plan):
        self._plan = plan

    def plan(self, message, transcript, presets, filter_fields):
        return self._plan


class _CitesFirstHit:
    def draft(self, question, hits, persona, transcript):
        return {"answer": "Nexus uses tiered pricing.", "citations": [hits[0]["id"]]}


class _FakeEmbedder:
    """Zero-vector embedder so the semantic retrieval arm runs offline (no OpenAI)."""

    def embed(self, texts):
        return [[0.0] * 1536 for _ in texts]


def _patch_models(monkeypatch, plan, draft):
    from app.services import chat_service
    monkeypatch.setattr(chat_service, "_build_plan_model", lambda: _CannedPlan(plan))
    monkeypatch.setattr(chat_service, "_build_draft_model", lambda: draft)
    monkeypatch.setattr(chat_service, "_build_embedder", lambda: _FakeEmbedder())


def test_answer_chat_returns_grounded_answer_with_real_sources(session, seeded_corpus, monkeypatch):
    from app.services.chat_service import answer_chat

    plan = {"expanded_query": "How is Sonatype Nexus priced?",
            "steps": [{"tool": "retrieve", "query": "nexus pricing tiers", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "pricing"}]}
    _patch_models(monkeypatch, plan, _CitesFirstHit())
    out = answer_chat(session, "how is it priced?",
                      history=[{"role": "user", "content": "Tell me about Sonatype Nexus"}])
    assert out["grounded"] is True
    assert out["answer"] == "Nexus uses tiered pricing."
    assert len(out["sources"]) == 1
    assert out["sources"][0]["source_url"] == "https://sonatype.com/pricing"
    assert out["plan"]["expanded_query"] == "How is Sonatype Nexus priced?"


def test_answer_chat_refuses_cleanly_when_corpus_lacks_it(session, seeded_corpus, monkeypatch):
    from app.services.chat_service import answer_chat

    plan = {"expanded_query": "Sonatype 2099 revenue forecast",
            "steps": [{"tool": "retrieve", "query": "sonatype 2099 revenue forecast", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "forecast"}]}

    class _Fabricator:
        def draft(self, question, hits, persona, transcript):
            return {"answer": "It will be $1B.", "citations": ["not-a-real-id"]}

    _patch_models(monkeypatch, plan, _Fabricator())
    out = answer_chat(session, "what is their 2099 revenue?")
    assert out["grounded"] is False
    assert out["sources"] == []
    assert out["reason"]


def test_seeded_finding_is_retrievable_by_the_chat_path(session, seeded_corpus, monkeypatch):
    """Corpus verification: findings written via index_finding are retrievable."""
    from app.services.research import provenance
    from app.services.chat_service import answer_chat

    class FakeEmbedder:
        def embed(self, texts):
            return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())
    provenance.index_finding(
        session, record_type="signal", record_id=999, text="Sonatype announced a malware firewall.",
        entity_id=seeded_corpus["sonatype"].id, signal_type="security_trust",
        published_at=datetime.now(UTC), reliability_grade="B",
    )
    session.flush()

    plan = {"expanded_query": "Sonatype malware firewall",
            "steps": [{"tool": "retrieve", "query": "sonatype malware firewall", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "security"}]}

    class _CitesMalware:
        def draft(self, question, hits, persona, transcript):
            match = next(h for h in hits if "malware firewall" in h["text"])
            return {"answer": "Sonatype shipped a malware firewall.", "citations": [match["id"]]}

    _patch_models(monkeypatch, plan, _CitesMalware())
    out = answer_chat(session, "did sonatype ship a malware firewall?")
    assert out["grounded"] is True
    assert any("malware firewall" in s["quote"] for s in out["sources"])


def test_post_chat_endpoint_returns_the_payload(session, seeded_corpus, monkeypatch):
    from fastapi.testclient import TestClient

    from app.db.session import get_session
    from app.main import app
    from app.services import chat_service

    plan = {"expanded_query": "How is Sonatype Nexus priced?",
            "steps": [{"tool": "retrieve", "query": "nexus pricing tiers", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "pricing"}]}
    monkeypatch.setattr(chat_service, "_build_plan_model", lambda: _CannedPlan(plan))
    monkeypatch.setattr(chat_service, "_build_draft_model", lambda: _CitesFirstHit())
    monkeypatch.setattr(chat_service, "_build_embedder", lambda: _FakeEmbedder())

    app.dependency_overrides[get_session] = lambda: session
    try:
        client = TestClient(app)
        resp = client.post("/chat", json={
            "message": "how is it priced?",
            "history": [{"role": "user", "content": "Tell me about Sonatype Nexus"}],
            "conversation_id": "conv-1",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["grounded"] is True
        assert body["conversation_id"] == "conv-1"
        assert body["plan"]["expanded_query"] == "How is Sonatype Nexus priced?"
        assert len(body["sources"]) == 1
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_citation_links_to_chunk_origin_url(session, seeded_corpus, monkeypatch):
    """A research chunk (no Source row) cites the live URL it was gathered from,
    with a domain-derived source name — not an empty link back to our own app."""
    from app.services.chat_service import answer_chat

    session.add(
        Chunk(record_type="signal", record_id=555, source_id=None,
              url="https://www.example.com/news/sonatype-firewall",
              entity_id=seeded_corpus["sonatype"].id,
              text="Sonatype launched a new malware firewall for open source.",
              prefix="security", reliability_grade="B", content_hash="chat-url-1"),
    )
    session.flush()

    plan = {"expanded_query": "sonatype malware firewall",
            "steps": [{"tool": "retrieve", "query": "sonatype malware firewall", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "security"}]}

    class _CitesUrlChunk:
        def draft(self, question, hits, persona, transcript):
            match = next(h for h in hits if "malware firewall" in h["text"])
            return {"answer": "Sonatype shipped a malware firewall.", "citations": [match["id"]]}

    _patch_models(monkeypatch, plan, _CitesUrlChunk())
    out = answer_chat(session, "did sonatype ship a firewall?")
    assert out["grounded"] is True
    src = out["sources"][0]
    assert src["source_url"] == "https://www.example.com/news/sonatype-firewall"
    assert src["source_name"] == "example.com"
    assert src["citation"]["source_url"] == "https://www.example.com/news/sonatype-firewall"


def test_retrieve_passes_embedder_so_semantic_arm_runs(session, seeded_corpus, monkeypatch):
    """Regression: retrieval must run the semantic arm. Without an embedder every
    turn refused with no_hits on paraphrased queries."""
    from app.services import chat_service

    calls = {"embed": 0}

    class _SpyEmbedder:
        def embed(self, texts):
            calls["embed"] += 1
            return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(chat_service, "_build_embedder", lambda: _SpyEmbedder())
    deps = chat_service._build_deps(session)
    deps.retrieve(query="how sonatype prices nexus", preset="ask_ledger",
                  filters={"entity_ids": [seeded_corpus["sonatype"].id]})
    assert calls["embed"] >= 1


class _StreamsThenCites:
    """Fake streaming draft model: yields answer token deltas then a final citation."""

    def __init__(self, chunks, cite_first=True):
        self._chunks = chunks
        self._cite_first = cite_first

    def stream(self, question, hits, persona, transcript):
        for c in self._chunks:
            yield ("token", c)
        cites = [hits[0]["id"]] if self._cite_first else ["not-a-real-id"]
        yield ("final", {"answer": "".join(self._chunks), "citations": cites})


def _patch_stream(monkeypatch, plan, stream_model):
    from app.services import chat_service
    monkeypatch.setattr(chat_service, "_build_plan_model", lambda: _CannedPlan(plan))
    monkeypatch.setattr(chat_service, "_build_draft_stream_model", lambda: stream_model)
    monkeypatch.setattr(chat_service, "_build_embedder", lambda: _FakeEmbedder())


def test_answer_chat_stream_emits_tokens_then_grounded_done(session, seeded_corpus, monkeypatch):
    from app.services.chat_service import answer_chat_stream

    plan = {"expanded_query": "How is Sonatype Nexus priced?",
            "steps": [{"tool": "retrieve", "query": "nexus pricing tiers", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "pricing"}]}
    _patch_stream(monkeypatch, plan, _StreamsThenCites(["Nexus ", "uses ", "tiered pricing."]))

    events = list(answer_chat_stream(session, "how is it priced?", conversation_id="c1"))
    kinds = [e["type"] for e in events]
    assert kinds[0] == "plan"
    assert "token" in kinds
    tokens = "".join(e["text"] for e in events if e["type"] == "token")
    assert tokens == "Nexus uses tiered pricing."
    done = events[-1]
    assert done["type"] == "done"
    assert done["grounded"] is True
    assert len(done["sources"]) == 1
    assert done["conversation_id"] == "c1"


def test_answer_chat_stream_refuses_when_citations_not_grounded(session, seeded_corpus, monkeypatch):
    from app.services.chat_service import answer_chat_stream

    plan = {"expanded_query": "Sonatype pricing",
            "steps": [{"tool": "retrieve", "query": "nexus pricing tiers", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "pricing"}]}
    _patch_stream(monkeypatch, plan, _StreamsThenCites(["It ", "is ", "$1B."], cite_first=False))

    done = list(answer_chat_stream(session, "what is it priced?"))[-1]
    assert done["type"] == "done"
    assert done["grounded"] is False
    assert done["sources"] == []
    assert done["reason"]


def test_chat_llm_roles_are_configured():
    from app.config.loader import load_config

    calls = load_config().llm.calls
    assert "chat_plan" in calls
    assert "chat_draft" in calls
    assert calls["chat_plan"].temperature == 0
    assert calls["chat_draft"].temperature == 0


def test_ask_still_answers_in_its_legacy_shape(session, seeded_corpus, monkeypatch):
    from app.services import chat_service
    from app.services.ask_service import answer_question

    plan = {"expanded_query": "How is Sonatype Nexus priced?",
            "steps": [{"tool": "retrieve", "query": "nexus pricing tiers", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "pricing"}]}
    monkeypatch.setattr(chat_service, "_build_plan_model", lambda: _CannedPlan(plan))
    monkeypatch.setattr(chat_service, "_build_draft_model", lambda: _CitesFirstHit())
    monkeypatch.setattr(chat_service, "_build_embedder", lambda: _FakeEmbedder())

    out = answer_question(session, "how is sonatype nexus priced?")
    # legacy keys the current /ask consumers rely on
    assert out["grounded"] is True
    assert out["question"] == "how is sonatype nexus priced?"
    assert isinstance(out["evidence"], list) and len(out["evidence"]) == 1
    assert out["refusal_reason"] is None
    assert "nearby_evidence" in out
