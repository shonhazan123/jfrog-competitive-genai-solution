from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.services.industry_themes import assign_theme, list_themes

THEMES = [
    {
        "key": "supply_chain_attacks",
        "label": "Supply-chain attacks & CVEs",
        "match": {
            "signal_types": ["security_trust"],
            "keywords": ["cve", "malware", "compromise", "exploit"],
        },
        "jfrog_relevance": "Raises demand for provenance and blocking at the gate — Curation and Xray.",
    },
    {
        "key": "regulation",
        "label": "Regulation & compliance",
        "match": {
            "signal_types": ["market_regulatory"],
            "keywords": ["cra", "sbom", "mandate", "executive order"],
        },
        "jfrog_relevance": "SBOM mandates map directly to AppTrust's evidence story.",
    },
    {
        "key": "funding_ma",
        "label": "Funding & acquisitions",
        "match": {
            "signal_types": ["corporate_financial"],
            "keywords": ["acquires", "funding", "raises", "series"],
        },
        "jfrog_relevance": "Consolidation reshapes the competitive set.",
    },
    {
        "key": "ai_mlops",
        "label": "AI / MLOps & model registries",
        "match": {
            "signal_types": ["product_capability"],
            "keywords": ["model", "mlops", "registry", "llm"],
        },
        "jfrog_relevance": "Validates JFrog ML / AI Catalog as the next artifact frontier.",
    },
]

EXPECTED_KEYS = [theme["key"] for theme in THEMES]


@pytest.fixture(autouse=True)
def _themes_config_dir(monkeypatch):
    repo_config = Path(__file__).resolve().parents[1] / "config"
    app_config = Path("/app/config")
    if (repo_config / "themes.yaml").exists():
        config_dir = repo_config
    elif (app_config / "themes.yaml").exists():
        config_dir = app_config
    else:
        pytest.fail("themes.yaml not found under repo config or /app/config")
    monkeypatch.setattr("app.settings.settings.config_dir", str(config_dir))


def test_assign_theme_maps_regulatory_sbom_to_regulation():
    item = {
        "signal_type": "market_regulatory",
        "headline": "New SBOM reporting rule proposed",
        "body": "Industry body copy.",
    }
    assert assign_theme(item, THEMES) == "regulation"


def test_assign_theme_returns_none_when_unmatched():
    item = {
        "signal_type": "partnership_ecosystem",
        "headline": "Cloud marketplace listing",
        "body": "Partnership framing.",
    }
    assert assign_theme(item, THEMES) is None


def test_list_themes_returns_stable_yaml_order_with_counts(session):
    from app.models.registry import Entity, Source
    from app.services.seeding import seed

    seed(session)
    entities = {entity.slug: entity for entity in session.query(Entity).all()}
    industry_entity = entities["industry"]
    now = datetime(2026, 8, 26, 6, 0, tzinfo=UTC)

    source = session.query(Source).filter_by(entity_id=industry_entity.id).first()
    if source is None:
        source = Source(
            key="industry_fixture",
            entity_id=industry_entity.id,
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

    from app.models.signal import Signal

    session.add_all(
        [
            Signal(
                source_id=source.id,
                entity_id=industry_entity.id,
                signal_type="market_regulatory",
                headline="EU CRA SBOM mandate update",
                occurred_at=now,
                cluster_key="industry-regulation",
                score_sales=50.0,
                score_product=50.0,
                score_exec=50.0,
                so_what_product="Regulatory framing.",
            ),
            Signal(
                source_id=source.id,
                entity_id=industry_entity.id,
                signal_type="security_trust",
                headline="Critical CVE in build tooling",
                occurred_at=now,
                cluster_key="industry-security",
                score_sales=50.0,
                score_product=50.0,
                score_exec=50.0,
                so_what_product="Security framing.",
            ),
            Signal(
                source_id=source.id,
                entity_id=industry_entity.id,
                signal_type="partnership_ecosystem",
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
    assert [theme["key"] for theme in themes[: len(EXPECTED_KEYS)]] == EXPECTED_KEYS
    assert themes[0] == {
        "key": "supply_chain_attacks",
        "label": "Supply-chain attacks & CVEs",
        "count": 1,
        "state_of_play": "1 items — Supply-chain attacks & CVEs",
        "jfrog_relevance": THEMES[0]["jfrog_relevance"],
    }
    assert themes[1]["count"] == 1
    assert themes[1]["state_of_play"] == "1 items — Regulation & compliance"
    assert themes[2]["count"] == 0
    assert themes[3]["count"] == 0
    assert themes[-1]["key"] == "other"
    assert themes[-1]["count"] == 1
