from agent.graphs.research.skeleton import run_research


class FakeDeps:
    max_attempts = 3

    def __init__(self):
        self.search_calls = {}

    def plan(self):
        return [
            {"id": "hit_first_try"},
            {"id": "needs_search"},
            {"id": "never"},
            {"id": "empty_search"},
        ]

    def collect(self, target):
        return {"structured": True} if target["id"] == "hit_first_try" else None

    def search(self, target):
        self.search_calls[target["id"]] = self.search_calls.get(target["id"], 0) + 1
        if target["id"] == "empty_search":
            return []
        return {"web": target["id"]}

    def assess(self, target, material, attempts):
        if target["id"] == "hit_first_try":
            return "resolved", {"id": target["id"], "src": "structured"}
        if target["id"] == "needs_search":
            # unresolved until a search has happened, then resolved
            if material and material.get("web"):
                return "resolved", {"id": target["id"], "src": "web"}
            return "unresolved", None
        return "unresolved", None  # 'never' never resolves

    def absent_draft(self, target):
        return {"id": target["id"], "absent": True}


def test_resolved_absent_and_cap():
    deps = FakeDeps()
    drafts = run_research(deps)
    by_id = {d["id"]: d for d in drafts}

    assert by_id["hit_first_try"]["src"] == "structured"   # structured tier, no search
    assert by_id["needs_search"]["src"] == "web"           # fell back to search, resolved
    assert by_id["never"]["absent"] is True                # exhausted -> absent, not fabricated
    assert deps.search_calls["never"] == deps.max_attempts # capped at 3 searches
    assert "hit_first_try" not in deps.search_calls        # structured hit never searched
    assert by_id["empty_search"]["absent"] is True
    assert deps.search_calls["empty_search"] == 1          # empty hits -> absent, no retry loop
