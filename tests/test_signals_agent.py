import json

from app.services.collection.fetcher import FetchResult


class _FakeFetcher:
    """Returns Lever-shaped JSON for sonatype_jobs."""

    def fetch(self, url, etag=None, last_modified=None):
        body = json.dumps(
            [
                {
                    "id": "job-1",
                    "text": "Enterprise Sales Director",
                    "createdAt": 1724000000000,
                    "hostedUrl": "https://jobs.lever.co/sonatype/job-1",
                    "categories": {"team": "Sales", "location": "EMEA"},
                }
            ]
        ).encode()
        return FetchResult(url, 200, body, None, None, False)


def test_structured_for_uses_lever_when_a_jobs_source_exists(session):
    from app.services.research.signals_agent import structured_for
    from app.services.seeding import seed

    seed(session)
    fn = structured_for(session, fetcher=_FakeFetcher())
    hiring = {"competitor": "sonatype", "sub_type": "hiring", "signal_type": "talent_org"}
    pricing = {"competitor": "sonatype", "sub_type": "pricing", "signal_type": "pricing_packaging"}
    assert fn(hiring) is not None      # sonatype_jobs (Lever) exists
    assert fn(pricing) is None         # no pricing adapter -> skeleton will search


def test_persist_signals_writes_cards_and_indexes(session, monkeypatch):
    from app.models.registry import Entity
    from app.models.signal import Signal
    from app.services.research import provenance, signals_agent
    from app.services.seeding import seed

    seed(session)

    class FakeEmbedder:
        def embed(self, texts):
            return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())
    drafts = [
        {
            "competitor": "sonatype",
            "signal_type": "talent_org",
            "headline": "h",
            "so_what": "s",
            "why_it_matters": "w",
            "tags": ["SALES"],
            "source_url": "https://x/a",
        },
        {"competitor": "snyk", "sub_type": "pricing", "absent": True},  # skipped
    ]
    n = signals_agent.persist_signals(session, drafts)
    session.flush()
    sonatype = session.query(Entity).filter_by(slug="sonatype").one()
    assert n == 1
    assert session.query(Signal).filter_by(entity_id=sonatype.id, signal_type="talent_org").count() == 1


def test_persist_signals_strips_nul_bytes_from_web_search_text(session, monkeypatch):
    """Regression: web-search text with a NUL (0x00) byte must not blow up the
    capture or Signal inserts (PostgreSQL rejects NUL in text/varchar columns)."""
    from app.models.registry import Entity
    from app.models.signal import Signal
    from app.services.research import provenance, signals_agent
    from app.services.seeding import seed

    seed(session)

    class FakeEmbedder:
        def embed(self, texts):
            return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())
    drafts = [
        {
            "competitor": "sonatype",
            "signal_type": "talent_org",
            "headline": "Aqua\x00Trivy advisory",
            "so_what": "path-traversal\x00 disclosed\x07",
            "why_it_matters": "real-world\x00 impact",
            "tags": ["SALES"],
            "source_url": "https://x/a",
        },
    ]
    n = signals_agent.persist_signals(session, drafts)
    session.flush()
    sonatype = session.query(Entity).filter_by(slug="sonatype").one()
    signal = session.query(Signal).filter_by(entity_id=sonatype.id).one()
    assert n == 1
    assert "\x00" not in signal.headline
    assert "\x00" not in signal.so_what_sales
    assert "\x00" not in signal.why_it_matters
