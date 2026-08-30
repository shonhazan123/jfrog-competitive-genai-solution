from types import SimpleNamespace

from app.controllers.today import _diversify


def _sig(entity: str, signal_type: str, score: float, theme: str | None = None):
    return SimpleNamespace(
        entity_id=entity, signal_type=signal_type, theme_key=theme, _score=score
    )


_SCORE = lambda s: s._score  # noqa: E731


def test_diversify_collapses_duplicate_entity_and_type_to_the_best():
    # Three near-identical hiring posts from the same rival collapse to one card,
    # so Today never shows the same company's hiring signal three times over.
    signals = [
        _sig("sonatype", "talent_org", 10),
        _sig("sonatype", "talent_org", 30),
        _sig("sonatype", "talent_org", 20),
    ]
    out = _diversify(
        signals,
        group_of=lambda s: s.signal_type,
        order=["talent_org"],
        per_group=3,
        total=12,
        collapse_key=lambda s: (s.entity_id, s.signal_type),
        score=_SCORE,
    )
    assert len(out) == 1
    assert out[0]._score == 30


def test_diversify_spreads_across_types_before_going_deep():
    signals = [
        _sig("a", "talent_org", 100),
        _sig("b", "talent_org", 90),
        _sig("c", "pricing_packaging", 80),
        _sig("d", "security_trust", 70),
    ]
    out = _diversify(
        signals,
        group_of=lambda s: s.signal_type,
        order=["talent_org", "pricing_packaging", "security_trust"],
        per_group=3,
        total=12,
        collapse_key=lambda s: (s.entity_id, s.signal_type),
        score=_SCORE,
    )
    kinds = [s.signal_type for s in out]
    # One of every kind comes first, before a second card of any single kind.
    assert kinds[:3] == ["talent_org", "pricing_packaging", "security_trust"]
    assert kinds[3] == "talent_org"


def test_diversify_respects_total_cap_best_first():
    signals = [_sig(str(i), "talent_org", i) for i in range(10)]
    out = _diversify(
        signals,
        group_of=lambda s: s.signal_type,
        order=["talent_org"],
        per_group=10,
        total=4,
        collapse_key=None,
        score=_SCORE,
    )
    assert [s._score for s in out] == [9, 8, 7, 6]


def test_diversify_groups_industry_by_theme():
    signals = [
        _sig("industry", "security_trust", 50, theme="supply_chain_vulns"),
        _sig("industry", "product_capability", 40, theme="ai_secops"),
        _sig("industry", "security_trust", 30, theme="supply_chain_vulns"),
    ]
    out = _diversify(
        signals,
        group_of=lambda s: s.theme_key,
        order=["supply_chain_vulns", "ai_secops"],
        per_group=2,
        total=8,
        score=_SCORE,
    )
    themes = [s.theme_key for s in out]
    # Themes lead the ordering, not the raw signal type, and both are represented.
    assert themes[:2] == ["supply_chain_vulns", "ai_secops"]
    assert set(themes) == {"supply_chain_vulns", "ai_secops"}
