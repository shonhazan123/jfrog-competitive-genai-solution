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


def _patch_models(monkeypatch, plan, draft):
    from app.services import chat_service
    monkeypatch.setattr(chat_service, "_build_plan_model", lambda: _CannedPlan(plan))
    monkeypatch.setattr(chat_service, "_build_draft_model", lambda: draft)


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
