def test_start_all_tags_a_batch_and_active_batch_recovers_it(monkeypatch):
    import app.controllers.runs as runs
    monkeypatch.setattr(runs, "_run_surface", lambda run_id, kind: None)  # don't actually run
    body = runs.start_all()
    assert "batch_id" in body and set(body["run_ids"]) == {"industry", "signals", "comparison"}
    active = runs.active_batch()
    assert active["batch_id"] == body["batch_id"]
    assert {r["surface"] for r in active["runs"]} == {"industry", "signals", "comparison"}


def test_start_all_runs_the_three_surfaces_concurrently(monkeypatch):
    import threading
    import app.controllers.runs as runs

    barrier = threading.Barrier(3, timeout=5)

    def blocking_surface(run_id, kind):
        barrier.wait()  # only releases if all three threads reach it together

    monkeypatch.setattr(runs, "_run_surface", blocking_surface)
    # Synchronous path fans out to threads; if they ran sequentially the barrier
    # would time out and raise BrokenBarrierError, failing the test.
    runs.start_all()
