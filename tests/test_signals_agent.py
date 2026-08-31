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


def test_persist_signals_dedupes_duplicate_events(session, monkeypatch):
    """N framings of one event (same competitor + signal_type, near-identical
    headlines) collapse into one signal with corroboration_count = N and N
    evidence rows — one per source."""
    from app.models.registry import Entity
    from app.models.signal import Signal, SignalEvidence
    from app.services.research import provenance, signals_agent
    from app.services.seeding import seed

    seed(session)

    class FakeEmbedder:
        def embed(self, texts):
            return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())

    def draft(headline, url):
        return {
            "competitor": "checkmarx",
            "signal_type": "corporate_financial",
            "headline": headline,
            "so_what": "s",
            "why_it_matters": "w",
            "tags": ["FUNDING"],
            "source_url": url,
        }

    drafts = [
        draft("Hellman & Friedman completes acquisition of Checkmarx", "https://x/1"),
        draft("Hellman & Friedman completes the acquisition of Checkmarx", "https://x/2"),
        draft("Hellman & Friedman completes acquisition of Checkmarx today", "https://x/3"),
    ]
    n = signals_agent.persist_signals(session, drafts)
    session.flush()

    checkmarx = session.query(Entity).filter_by(slug="checkmarx").one()
    sigs = session.query(Signal).filter_by(entity_id=checkmarx.id).all()
    assert n == 1 and len(sigs) == 1
    assert sigs[0].corroboration_count == 3
    assert session.query(SignalEvidence).filter_by(signal_id=sigs[0].id).count() == 3


def test_persist_signals_keeps_distinct_events_separate(session, monkeypatch):
    """Two different events for the same competitor stay as two signals."""
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
        {"competitor": "snyk", "signal_type": "talent_org", "headline": "Snyk hiring senior sales engineers",
         "so_what": "s", "why_it_matters": "w", "tags": [], "source_url": "https://x/1"},
        {"competitor": "snyk", "signal_type": "talent_org", "headline": "Snyk opens new research office in Boston",
         "so_what": "s", "why_it_matters": "w", "tags": [], "source_url": "https://x/2"},
    ]
    n = signals_agent.persist_signals(session, drafts)
    session.flush()

    snyk = session.query(Entity).filter_by(slug="snyk").one()
    assert n == 2
    assert session.query(Signal).filter_by(entity_id=snyk.id).count() == 2
