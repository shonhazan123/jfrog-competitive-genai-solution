import pytest
from datetime import UTC, datetime
from fastapi.testclient import TestClient
from app.main import app
from app.models.run import Run, load_run_stages, put_run


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def running_run():
    stages = load_run_stages()
    run = Run(
        id="run_test_running",
        stage_key=stages[1]["key"],
        current=1,
        total=len(stages),
        status="running",
        started_at=datetime(2026, 8, 26, 6, 0, tzinfo=UTC),
    )
    put_run(run)
    return run


@pytest.fixture
def finished_run():
    stages = load_run_stages()
    run = Run(
        id="run_test_finished",
        stage_key=stages[-1]["key"],
        current=len(stages) - 1,
        total=len(stages),
        status="done",
        new_items=11,
        started_at=datetime(2026, 8, 26, 6, 0, tzinfo=UTC),
        finished_at=datetime(2026, 8, 26, 6, 5, tzinfo=UTC),
    )
    put_run(run)
    return run


@pytest.fixture
def failed_run():
    stages = load_run_stages()
    run = Run(
        id="run_test_failed",
        stage_key=stages[0]["key"],
        current=0,
        total=len(stages),
        status="failed",
        message="Could not reach 2 of 23 sources",
        started_at=datetime(2026, 8, 26, 6, 0, tzinfo=UTC),
        finished_at=datetime(2026, 8, 26, 6, 1, tzinfo=UTC),
    )
    put_run(run)
    return run


def test_post_runs_returns_immediately_with_a_run_id(client):
    response = client.post("/runs", json={"kind": "collect"})
    assert response.status_code == 202
    assert response.json()["run_id"]


def test_progress_reports_a_human_stage_never_a_layer_name(client, running_run):
    body = client.get(f"/runs/{running_run.id}").json()
    labels = {stage["label"] for stage in load_run_stages()}
    assert body["stage_label"] in labels
    assert "_" not in body["stage_label"]


def test_progress_carries_counters_so_the_ui_can_show_movement(client, running_run):
    body = client.get(f"/runs/{running_run.id}").json()
    assert {"current", "total"} <= set(body["progress"])


def test_a_finished_run_reports_what_it_produced(client, finished_run):
    body = client.get(f"/runs/{finished_run.id}").json()
    assert body["status"] == "done"
    assert body["new_items"] >= 0


def test_a_failed_run_surfaces_a_readable_message_not_a_traceback(client, failed_run):
    body = client.get(f"/runs/{failed_run.id}").json()
    assert body["status"] == "failed"
    assert "Traceback" not in body["message"]


def test_new_items_from_report_sums_surface_counts():
    from app.controllers.runs import _new_items_from_report

    report = {
        "captures": 3,
        "industry_items": 4,
        "signals_items": 5,
        "comparison_items": 2,
    }
    assert _new_items_from_report(report) == 14
    assert _new_items_from_report({"scored": 7}) == 7
