def test_persist_industry_writes_signals_with_theme_key_and_indexes(session, monkeypatch):
    from app.models.delivery import Chunk
    from app.models.registry import Entity
    from app.models.signal import Signal
    from app.services.research import industry_agent, provenance
    from app.services.seeding import seed

    seed(session)

    class FakeEmbedder:
        def embed(self, texts):
            return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())

    drafts = [
        {
            "bucket": "supply_chain_vulns",
            "signal_type": "security_trust",
            "items": [
                {
                    "headline": "Malicious npm pkg",
                    "body": "b",
                    "why_it_matters": "w",
                    "source_url": "https://x/a",
                }
            ],
        },
        {
            "bucket": "ai_secops",
            "signal_type": "security_trust",
            "items": [],  # absent bucket
        },
    ]

    n = industry_agent.persist_industry(session, drafts)
    session.flush()

    industry = session.query(Entity).filter_by(slug="industry").one()
    sigs = session.query(Signal).filter_by(entity_id=industry.id).all()
    assert n == 1 and len(sigs) == 1
    assert sigs[0].theme_key == "supply_chain_vulns"
    assert sigs[0].why_it_matters == "w"
    assert session.query(Chunk).filter_by(record_type="signal", record_id=sigs[0].id).count() == 1


def test_persist_industry_dedupes_duplicate_events(session, monkeypatch):
    """N framings of one industry event collapse into one signal with
    corroboration_count = N and N evidence rows."""
    from app.models.registry import Entity
    from app.models.signal import Signal, SignalEvidence
    from app.services.research import industry_agent, provenance
    from app.services.seeding import seed

    seed(session)

    class FakeEmbedder:
        def embed(self, texts):
            return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())

    def item(headline, url):
        return {"headline": headline, "body": "b", "why_it_matters": "w", "source_url": url}

    drafts = [
        {
            "bucket": "supply_chain_vulns",
            "signal_type": "security_trust",
            "items": [
                item("Mini Shai-Hulud multi-ecosystem package attack disclosed", "https://x/1"),
                item("Mini Shai-Hulud: multi-ecosystem package attack disclosed", "https://x/2"),
                item("Mini Shai-Hulud multi-ecosystem package attack disclosed today", "https://x/3"),
            ],
        }
    ]

    n = industry_agent.persist_industry(session, drafts)
    session.flush()

    industry = session.query(Entity).filter_by(slug="industry").one()
    sigs = session.query(Signal).filter_by(entity_id=industry.id).all()
    assert n == 1 and len(sigs) == 1
    assert sigs[0].corroboration_count == 3
    assert session.query(SignalEvidence).filter_by(signal_id=sigs[0].id).count() == 3
