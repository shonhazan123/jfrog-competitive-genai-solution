def test_build_cells_is_five_by_five():
    from app.services.research.comparison_agent import build_cells

    cells = build_cells()
    assert len(cells) == 25
    assert {c["competitor"] for c in cells} == {"github", "sonatype", "snyk", "aqua", "checkmarx"}


def test_persist_comparison_upserts_claim_with_stance_and_skips_none(session, monkeypatch):
    from app.models.ledger import Claim
    from app.models.registry import Entity
    from app.services.research import comparison_agent, provenance
    from app.services.seeding import seed

    seed(session)

    class FakeEmbedder:
        def embed(self, texts):
            return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())
    drafts = [
        {
            "competitor": "sonatype",
            "dimension": "artifact_management",
            "stance": "moderate",
            "summary": "Nexus Repository",
            "source_url": "https://x/nexus",
        },
        {"competitor": "snyk", "dimension": "artifact_management", "stance": "none"},  # skipped
    ]
    n = comparison_agent.persist_comparison(session, drafts)
    session.flush()
    sonatype = session.query(Entity).filter_by(slug="sonatype").one()
    jfrog = session.query(Entity).filter_by(slug="jfrog").one()
    claim = session.query(Claim).filter_by(
        asserting_entity_id=sonatype.id,
        subject_entity_id=jfrog.id,
        dimension="artifact_management",
    ).one()
    assert n == 1 and claim.stance == "moderate" and claim.claim_text == "Nexus Repository"
    comparison_agent.persist_comparison(session, drafts)
    session.flush()
    assert session.query(Claim).filter_by(
        asserting_entity_id=sonatype.id,
        dimension="artifact_management",
    ).count() == 1
