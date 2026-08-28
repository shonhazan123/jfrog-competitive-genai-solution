import threading

from agent.graphs.research.skeleton import run_research


class FakeDeps:
    max_attempts = 3

    def __init__(self):
        self.search_calls = {}
        self._lock = threading.Lock()

    def plan(self):
        return [
            {"id": "hit_first_try"},
            {"id": "needs_search"},
            {"id": "never"},
            {"id": "empty_search"},
        ]

    def collect(self, target):
        return {"structured": True} if target["id"] == "hit_first_try" else None

    def search(self, target, *, attempt=1):
        with self._lock:
            self.search_calls[target["id"]] = self.search_calls.get(target["id"], 0) + 1
        if target["id"] == "empty_search":
            return []
        return {"web": target["id"], "attempt": attempt}

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


class RetryBroadenDeps:
    max_attempts = 3

    def __init__(self):
        self.queries: list[int] = []

    def plan(self):
        return [{"id": "retry"}]

    def collect(self, target):
        return None

    def search(self, target, *, attempt=1):
        self.queries.append(attempt)
        return [{"hit": attempt}]

    def assess(self, target, material, attempts):
        if attempts >= 3:
            return "resolved", {"id": target["id"], "attempts": attempts}
        return "unresolved", None

    def absent_draft(self, target):
        return {"id": target["id"], "absent": True}


def test_retries_use_distinct_search_attempts():
    deps = RetryBroadenDeps()
    draft = run_research(deps)[0]
    assert draft["attempts"] == 3
    assert deps.queries == [1, 2, 3]


class FailingCollectDeps:
    max_attempts = 3

    def plan(self):
        return [
            {"id": "ok_first"},
            {"id": "boom"},
            {"id": "ok_last"},
        ]

    def collect(self, target):
        if target["id"] == "boom":
            raise ConnectionError("[Errno -2] Name or service not known")
        return {"structured": target["id"]}

    def search(self, target, *, attempt=1):
        raise AssertionError("search should not run when collect succeeds")

    def assess(self, target, material, attempts):
        return "resolved", {"id": target["id"], "resolved": True}

    def absent_draft(self, target):
        return {"id": target["id"], "absent": True}


def test_collect_failure_isolated_per_target():
    deps = FailingCollectDeps()
    drafts = run_research(deps)

    assert len(drafts) == 3
    assert drafts[0] == {"id": "ok_first", "resolved": True}
    assert drafts[1] == {"id": "boom", "absent": True}
    assert drafts[2] == {"id": "ok_last", "resolved": True}
