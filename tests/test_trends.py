from datetime import UTC, date, datetime, timedelta
from app.config.loader import load_config
from app.services.trends import compute_trends

CFG = load_config().trends
AS_OF = date(2026, 8, 26)

def sig(theme, weeks_ago, source_id=1, signal_id=None):
    return {"id": signal_id or (weeks_ago * 100 + source_id),
            "capability_tags": [theme], "source_id": source_id,
            "occurred_at": datetime.now(UTC) - timedelta(weeks=weeks_ago)}

def test_growing_volume_reads_as_rising():
    signals = ([sig("model_registry", 1, s) for s in range(1, 7)] +
               [sig("model_registry", 6, s) for s in range(1, 3)])
    trend = next(t for t in compute_trends(signals, CFG, AS_OF) if t.theme == "model_registry")
    assert trend.direction == "rising"

def test_near_zero_prior_volume_reads_as_emerging():
    signals = [sig("model_registry", 1, s) for s in range(1, 6)]
    trend = next(t for t in compute_trends(signals, CFG, AS_OF) if t.theme == "model_registry")
    assert trend.velocity == "emerging"

def test_a_theme_below_the_minimum_produces_no_trend():
    signals = [sig("sbom", 1)]
    assert [t for t in compute_trends(signals, CFG, AS_OF) if t.theme == "sbom"] == []

def test_confidence_requires_independent_sources_not_just_volume():
    """Ten signals from one source is not corroboration."""
    same_source = [sig("sbom", 1, source_id=1, signal_id=i) for i in range(10)]
    many_sources = [sig("sbom", 1, source_id=s, signal_id=100 + s) for s in range(1, 11)]
    assert compute_trends(same_source, CFG, AS_OF)[0].confidence != "high"
    assert compute_trends(many_sources, CFG, AS_OF)[0].confidence == "high"

def test_every_trend_lists_the_signals_that_produced_it():
    signals = [sig("sbom", 1, s) for s in range(1, 6)]
    trend = compute_trends(signals, CFG, AS_OF)[0]
    assert len(trend.contributing_signal_ids) == 5
