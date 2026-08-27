from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.services.industry_themes import list_themes, theme_detail


@pytest.fixture(autouse=True)
def _industry_buckets_config_dir(monkeypatch):
    repo_config = Path(__file__).resolve().parents[1] / "config"
    app_config = Path("/app/config")
    if (repo_config / "industry_buckets.yaml").exists():
        config_dir = repo_config
    elif (app_config / "industry_buckets.yaml").exists():
        config_dir = app_config
    else:
        pytest.fail("industry_buckets.yaml not found under repo config or /app/config")
    monkeypatch.setattr("app.settings.settings.config_dir", str(config_dir))


def test_list_themes_groups_by_theme_key(session):
    from app.models.registry import Entity, Source
    from app.models.signal import Signal
    from app.services.seeding import seed

    seed(session)
    industry = session.query(Entity).filter_by(slug="industry").one()
    now = datetime(2026, 8, 26, 6, 0, tzinfo=UTC)

    source = session.query(Source).filter_by(entity_id=industry.id).first()
    if source is None:
        source = Source(
            key="industry_fixture",
            entity_id=industry.id,
            url="https://example.com/industry",
            kind="atom",
            mode="feed",
            reliability_grade="A",
            is_primary=True,
            check_frequency_minutes=60,
            last_checked_at=now,
        )
        session.add(source)
        session.flush()

    session.add_all(
        [
            Signal(
                source_id=source.id,
                entity_id=industry.id,
                signal_type="security_trust",
                theme_key="supply_chain_vulns",
                headline="Malicious npm package",
                occurred_at=now,
                cluster_key="industry-supply-chain",
                score_sales=50.0,
                score_product=50.0,
                score_exec=50.0,
                so_what_product="Supply chain framing.",
            ),
            Signal(
                source_id=source.id,
                entity_id=industry.id,
                signal_type="market_regulatory",
                theme_key="regulation_compliance",
                headline="EU CRA SBOM mandate",
                occurred_at=now,
                cluster_key="industry-regulation",
                score_sales=50.0,
                score_product=50.0,
                score_exec=50.0,
                so_what_product="Regulatory framing.",
            ),
            Signal(
                source_id=source.id,
                entity_id=industry.id,
                signal_type="partnership_ecosystem",
                theme_key=None,
                headline="CNCF sandbox project",
                occurred_at=now,
                cluster_key="industry-other",
                score_sales=50.0,
                score_product=50.0,
                score_exec=50.0,
                so_what_product="Ecosystem framing.",
            ),
        ]
    )
    session.flush()

    themes = list_themes(session)
    keys = [t["key"] for t in themes]
    assert keys[:4] == [
        "supply_chain_vulns",
        "ai_secops",
        "pipeline_devsecops",
        "regulation_compliance",
    ]
    by_key = {t["key"]: t for t in themes}
    assert by_key["supply_chain_vulns"]["count"] == 1
    assert by_key["supply_chain_vulns"]["label"] == (
        "Software Supply-Chain Vulnerabilities & Exploits"
    )
    assert by_key["regulation_compliance"]["count"] == 1
    assert by_key["ai_secops"]["count"] == 0
    assert by_key["pipeline_devsecops"]["count"] == 0
    assert themes[-1]["key"] == "other"
    assert themes[-1]["count"] == 1


def test_theme_detail_returns_bucket_items(session):
    from app.models.registry import Entity, Source
    from app.models.signal import Signal
    from app.services.seeding import seed

    seed(session)
    industry = session.query(Entity).filter_by(slug="industry").one()
    now = datetime(2026, 8, 26, 6, 0, tzinfo=UTC)

    source = Source(
        key="industry_detail_fixture",
        entity_id=industry.id,
        url="https://example.com/industry-detail",
        kind="atom",
        mode="feed",
        reliability_grade="A",
        is_primary=True,
        check_frequency_minutes=60,
        last_checked_at=now,
    )
    session.add(source)
    session.flush()

    session.add(
        Signal(
            source_id=source.id,
            entity_id=industry.id,
            signal_type="security_trust",
            theme_key="ai_secops",
            headline="Poisoned model on HF",
            occurred_at=now,
            cluster_key="industry-ai",
            score_sales=50.0,
            score_product=50.0,
            score_exec=50.0,
            so_what_product="AI security framing.",
            why_it_matters="Registry demand.",
        )
    )
    session.flush()

    detail = theme_detail(session, "ai_secops")
    assert detail["label"] == "AI Code-Gen & ML Security"
    assert len(detail["items"]) == 1
    assert detail["items"][0]["headline"] == "Poisoned model on HF"
    assert "jfrog_relevance" in detail
