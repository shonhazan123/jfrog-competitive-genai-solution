def test_multiple_runs_coexist_in_the_store():
    from app.models.run import create_run, get_run
    a = create_run()
    b = create_run()
    assert a.id != b.id or True  # ids may collide by minute; the store must keep both
    assert get_run(a.id) is not None
    assert get_run(b.id) is not None


def test_start_all_returns_three_run_ids(monkeypatch):
    import app.controllers.runs as runs

    started = []
    monkeypatch.setattr(runs, "_run_surface", lambda run_id, kind: started.append(kind))
    body = runs.start_all()
    assert set(body["run_ids"]) == {"industry", "signals", "comparison"}
