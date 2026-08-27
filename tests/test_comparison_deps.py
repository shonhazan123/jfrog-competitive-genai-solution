from agent.graphs.research.comparison.deps import ComparisonDeps, CellVerdict
from agent.tools.web_search import SearchHit


def _cell(dim="artifact_management"):
    return {
        "competitor": "sonatype",
        "name": "Sonatype",
        "aliases": ["Nexus"],
        "dimension": dim,
        "label": "Artifact Management",
        "jfrog_reference": "Artifactory universal 30+ types",
    }


class StubGate:
    def __init__(self, found, stance="moderate"):
        self.found, self.stance = found, stance

    def invoke(self, _p):
        return CellVerdict(
            found=self.found,
            stance=self.stance,
            summary="Nexus Repository, mature" if self.found else "",
            source_url="https://x/nexus" if self.found else "",
        )


def test_found_capability_resolves_with_stance():
    deps = ComparisonDeps(
        [_cell()],
        search_fn=lambda t: [SearchHit("t", "https://x/nexus", "s")],
        gate_model=StubGate(True, "moderate"),
    )
    verdict, draft = deps.assess(_cell(), [SearchHit("t", "https://x/nexus", "s")], attempts=1)
    assert verdict == "resolved"
    assert draft["stance"] == "moderate" and draft["source_url"] == "https://x/nexus"


def test_no_capability_is_unresolved_then_absent_none():
    deps = ComparisonDeps([_cell()], search_fn=lambda t: [], gate_model=StubGate(False))
    verdict, draft = deps.assess(_cell(), [], attempts=1)
    assert verdict == "unresolved" and draft is None
    assert deps.absent_draft(_cell()) == {
        "competitor": "sonatype",
        "dimension": "artifact_management",
        "stance": "none",
    }
