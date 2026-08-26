import pytest
from datetime import UTC, datetime
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client_with_history(monkeypatch):
    from app.controllers import runs as runs_controller
    runs_controller._last_run_at = datetime(2026, 8, 26, 6, 0, tzinfo=UTC)
    runs_controller._next_run_at = datetime(2026, 8, 27, 6, 0, tzinfo=UTC)
    runs_controller._last_report = {"sources": 3, "captures": 2}
    return TestClient(app)

def test_run_status_reports_last_and_next_run(client_with_history):
    body = client_with_history.get("/runs/status").json()
    assert {"last_run_at", "next_run_at", "sources", "collected", "material"} <= set(body)
