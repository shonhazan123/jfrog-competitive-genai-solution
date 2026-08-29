from agent.graphs.research.skeleton import run_research


class Deps:  # minimal: 3 targets, all resolve immediately
    max_attempts = 3

    def plan(self):
        return [{"id": 1}, {"id": 2}, {"id": 3}]

    def collect(self, t):
        return {"ok": True}

    def search(self, t, *, attempt=1):
        return {"ok": True}

    def assess(self, t, m, a):
        return "resolved", {"id": t["id"]}

    def absent_draft(self, t):
        return {"id": t["id"], "absent": True}


def test_run_research_reports_plan_then_each_target():
    calls = []
    run_research(Deps(), progress=lambda step, current=None, total=None: calls.append((step, current, total)))
    assert calls[0] == ("plan", 0, 3)
    assert ("research", 1, 3) in calls and ("research", 3, 3) in calls
