import pytest

from app.config.loader import load_config

CFG = load_config()


@pytest.fixture
def fake_smtp():
    class _Fake:
        def __init__(self): self.sent = 0
        def send(self, **kwargs): self.sent += 1
    return _Fake()


def test_digest_job_writes_a_run_row_per_persona(session, fake_smtp):
    from worker.jobs import run_digest
    report = run_digest(session=session, smtp=fake_smtp)
    from app.models.delivery import DigestRun
    assert session.query(DigestRun).count() == 3

def test_exec_digest_only_runs_on_its_configured_day(session, fake_smtp, monkeypatch):
    """A daily executive email is how this product dies in week two."""
    from worker.jobs import personas_due
    monkeypatch.setattr("worker.jobs.today_name", lambda: "TUE")
    assert "exec" not in personas_due(cfg=CFG)
    monkeypatch.setattr("worker.jobs.today_name", lambda: "FRI")
    assert "exec" in personas_due(cfg=CFG)
