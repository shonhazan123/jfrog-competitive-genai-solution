from datetime import UTC, datetime, timedelta
from app.config.loader import load_config
from app.services.signals.clustering import cluster

CFG = load_config().materiality.cluster
DAY = datetime(2026, 8, 20, tzinfo=UTC)

def item(title, entity="sonatype", tags=("package_format_support",), day=DAY, grade="A"):
    return {"headline": title, "entity": entity, "capability_tags": list(tags),
            "occurred_at": day, "reliability_grade": grade, "is_primary": grade == "A"}

def test_the_same_event_from_five_sources_becomes_one_cluster():
    items = [item("Nexus 3.95 adds Cargo registry support"),
             item("Sonatype ships Cargo support in Nexus 3.95"),
             item("Nexus 3.95 released with Cargo registry", grade="C"),
             item("Cargo registry support arrives in Nexus 3.95", grade="C"),
             item("Nexus 3.95 adds Cargo registry", grade="B")]
    assert len(cluster(items, CFG)) == 1

def test_different_capabilities_do_not_cluster():
    items = [item("Nexus 3.95 adds Cargo registry support"),
             item("Nexus 3.95 adds model scanning", tags=("model_registry",))]
    assert len(cluster(items, CFG)) == 2

def test_different_entities_never_cluster():
    items = [item("Adds Cargo registry support"),
             item("Adds Cargo registry support", entity="harbor")]
    assert len(cluster(items, CFG)) == 2

def test_events_outside_the_window_do_not_cluster():
    items = [item("Nexus adds Cargo registry support"),
             item("Nexus adds Cargo registry support", day=DAY + timedelta(days=30))]
    assert len(cluster(items, CFG)) == 2

def test_the_best_source_is_first_in_its_cluster():
    """The representative is chosen by evidentiary value, not arrival order."""
    items = [item("Nexus 3.95 adds Cargo registry", grade="C"),
             item("Nexus 3.95 adds Cargo registry support", grade="A")]
    assert cluster(items, CFG)[0][0]["reliability_grade"] == "A"
