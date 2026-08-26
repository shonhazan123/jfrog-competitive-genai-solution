from datetime import UTC, datetime
from app.config.loader import load_config
from app.services.scoring.materiality import score

CONFIG = load_config()
NOW = datetime.now(UTC)

def facets(**overrides):
    base = dict(signal_type="product_capability", subject_entity="sonatype",
                asserting_entity="sonatype", entity_tier=1, reliability_grade="A",
                corroboration_count=1, capability_tags=[], occurred_at=NOW,
                change_kind=None, text="")
    return base | overrides

def test_routing_sends_capability_news_to_product_not_sales():
    f = facets()
    assert score(f, "product", CONFIG).total > score(f, "sales", CONFIG).total

def test_corporate_news_scores_zero_base_for_sales():
    f = facets(signal_type="corporate_financial")
    parts = dict(score(f, "sales", CONFIG).parts)
    assert parts["base"] == 0

def test_cross_assertion_about_jfrog_is_amplified_for_sales():
    normal = score(facets(signal_type="positioning_messaging"), "sales", CONFIG)
    about_us = score(facets(signal_type="positioning_messaging", subject_entity="jfrog"),
                     "sales", CONFIG)
    assert about_us.total > normal.total

def test_breakdown_sums_to_total_so_the_ui_can_render_arithmetic():
    breakdown = score(facets(), "product", CONFIG)
    assert abs(sum(v for _, v in breakdown.parts) - breakdown.total) < 1e-9

def test_watchlist_hit_adds_its_labelled_part():
    breakdown = score(facets(text="new MCP registry support"), "product", CONFIG)
    assert any(label.startswith("watchlist:") for label, _ in breakdown.parts)

def test_lowering_the_jfrog_modifier_re_ranks_without_touching_code():
    """Prioritisation is policy. An analyst may set this to 1.0."""
    tuned = CONFIG.model_copy(deep=True)
    tuned.materiality.modifiers["subject_is_jfrog"] = 1.0
    f = facets(signal_type="positioning_messaging", subject_entity="jfrog")
    assert score(f, "sales", tuned).total < score(f, "sales", CONFIG).total
