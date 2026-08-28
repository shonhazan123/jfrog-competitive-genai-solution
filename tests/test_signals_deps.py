from agent.graphs.research.signals.deps import SignalsDeps, SignalCard


def _t(sub="hiring"):
    return {
        "competitor": "sonatype",
        "name": "Sonatype",
        "aliases": ["Nexus"],
        "sub_type": sub,
        "signal_type": "talent_org",
    }


class StubGate:
    def __init__(self, usable):
        self.usable = usable

    def invoke(self, _p):
        if self.usable:
            return SignalCard(
                usable=True,
                headline="18 EMEA sales roles",
                so_what="GTM push",
                why_it_matters="hits JFrog's strongest segment",
                tags=["SALES"],
                source_url="https://x/jobs",
            )
        return SignalCard(
            usable=False,
            headline="",
            so_what="",
            why_it_matters="",
            tags=[],
            source_url="",
        )


def test_structured_hit_resolves_without_search():
    calls = []
    deps = SignalsDeps(
        [_t()],
        structured_fn=lambda t: [{"title": "role"}],
        search_fn=lambda t: calls.append(t) or [],
        gate_model=StubGate(True),
    )
    material = deps.collect(_t())
    assert material == [{"title": "role"}]
    verdict, draft = deps.assess(_t(), material, attempts=0)
    assert verdict == "resolved" and draft["source_url"] == "https://x/jobs"
    assert calls == []  # never fell back to search


def test_no_structured_source_returns_none_so_skeleton_searches():
    deps = SignalsDeps(
        [_t("pricing")],
        structured_fn=lambda t: None,
        search_fn=lambda t: [],
        gate_model=StubGate(True),
    )
    assert deps.collect(_t("pricing")) is None


def test_not_usable_is_unresolved():
    deps = SignalsDeps(
        [_t()],
        structured_fn=lambda t: [{"x": 1}],
        search_fn=lambda t: [],
        gate_model=StubGate(False),
    )
    verdict, draft = deps.assess(_t(), [{"x": 1}], attempts=1)
    assert verdict == "unresolved" and draft is None


def test_fabricated_web_source_url_does_not_resolve():
    from agent.tools.web_search import SearchHit

    deps = SignalsDeps(
        [_t("pricing")],
        structured_fn=lambda t: None,
        search_fn=lambda t: [SearchHit("t", "https://x/real", "s")],
        gate_model=StubGate(True),
    )
    verdict, draft = deps.assess(
        _t("pricing"),
        [SearchHit("t", "https://x/real", "s")],
        attempts=1,
    )
    assert verdict == "unresolved" and draft is None


def test_grounded_web_source_url_resolves():
    from agent.tools.web_search import SearchHit

    class GroundedGate:
        def invoke(self, _p):
            return SignalCard(
                usable=True,
                headline="h",
                so_what="s",
                why_it_matters="w",
                tags=[],
                source_url="https://x/real",
            )

    deps = SignalsDeps(
        [_t("pricing")],
        structured_fn=lambda t: None,
        search_fn=lambda t: [SearchHit("t", "https://x/real", "s")],
        gate_model=GroundedGate(),
    )
    verdict, draft = deps.assess(
        _t("pricing"),
        [SearchHit("t", "https://x/real", "s")],
        attempts=1,
    )
    assert verdict == "resolved"
    assert draft["source_url"] == "https://x/real"
