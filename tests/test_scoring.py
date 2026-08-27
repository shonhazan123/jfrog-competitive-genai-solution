from app.config.loader import load_config
from app.services.scoring.materiality import primary_stakeholder, tier_for


def test_tier_bands():
    cfg = load_config()
    assert tier_for(75, cfg) == "act_on_it"
    assert tier_for(40, cfg) == "worth_knowing"
    assert tier_for(10, cfg) == "background"


def test_primary_stakeholder_is_argmax_with_exec_tiebreak():
    assert primary_stakeholder({"sales": 10, "product": 50, "exec": 50}) == "exec"
    assert primary_stakeholder({"sales": 30, "product": 10, "exec": 5}) == "sales"
