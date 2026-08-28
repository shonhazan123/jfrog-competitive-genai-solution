from agent.graphs.research.industry.deps import IndustryDeps
from agent.tools.web_search import SearchHit


class StubGate:
    """Returns whatever items the test wants, ignoring the prompt."""

    def __init__(self, items):
        self._items = items

    def invoke(self, _prompt):
        from agent.graphs.research.industry.deps import IndustryAssessment

        return IndustryAssessment(kept=self._items)


def _bucket():
    return {
        "key": "ai_secops",
        "label": "AI Sec",
        "signal_type": "security_trust",
        "include": ["poisoned model"],
        "exclude": ["quantization"],
        "jfrog_relevance": "x",
    }


def test_gate_keeps_on_topic_items_and_resolves():
    from agent.graphs.research.industry.deps import IndustryItem

    items = [
        IndustryItem(
            headline="Malicious model on HF",
            body="b",
            why_it_matters="w",
            source_url="https://x/a",
        )
    ]
    deps = IndustryDeps([_bucket()], gate_model=StubGate(items), search=lambda t: [])
    verdict, draft = deps.assess(_bucket(), [SearchHit("t", "https://x/a", "s")], attempts=1)
    assert verdict == "resolved"
    assert draft["items"][0]["source_url"] == "https://x/a"
    assert draft["bucket"] == "ai_secops"


def test_gate_keeping_nothing_is_unresolved_then_absent():
    deps = IndustryDeps([_bucket()], gate_model=StubGate([]), search=lambda t: [])
    verdict, draft = deps.assess(_bucket(), [SearchHit("t", "https://x/a", "s")], attempts=1)
    assert verdict == "unresolved"     # nothing kept, but attempts remain -> retry
    assert draft is None


def test_absent_draft_is_empty_items():
    deps = IndustryDeps([_bucket()], gate_model=StubGate([]), search=lambda t: [])
    assert deps.absent_draft(_bucket()) == {
        "bucket": "ai_secops",
        "signal_type": "security_trust",
        "items": [],
    }


def test_fabricated_source_url_is_filtered_out():
    from agent.graphs.research.industry.deps import IndustryItem

    items = [
        IndustryItem(
            headline="Malicious model on HF",
            body="b",
            why_it_matters="w",
            source_url="https://x/fabricated",
        )
    ]
    deps = IndustryDeps([_bucket()], gate_model=StubGate(items), search=lambda t: [])
    verdict, draft = deps.assess(_bucket(), [SearchHit("t", "https://x/a", "s")], attempts=1)
    assert verdict == "unresolved" and draft is None
