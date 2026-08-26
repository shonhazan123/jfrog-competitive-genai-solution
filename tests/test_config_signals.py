import pytest
from pydantic import ValidationError
from app.config.loader import load_config
from app.config.schema import RoutingConfig

def test_every_signal_type_has_a_routing_row():
    config = load_config()
    for signal_type in config.signal_types.types:
        assert signal_type in config.routing.matrix, f"{signal_type} has no routing row"

def test_routing_covers_all_three_personas():
    config = load_config()
    for row in config.routing.matrix.values():
        assert set(row) == {"sales", "product", "exec"}

def test_relevance_outside_zero_to_three_is_rejected():
    with pytest.raises(ValidationError):
        RoutingConfig.model_validate(
            {"matrix": {"product_capability": {"sales": 9, "product": 3, "exec": 1}}}
        )

def test_digest_budget_is_present_for_every_persona():
    config = load_config()
    assert set(config.materiality.budget) == {"sales", "product", "exec"}
