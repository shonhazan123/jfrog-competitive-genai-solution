from datetime import UTC, datetime

import pytest

from app.config.loader import load_config
from app.services.delivery.assembly import Digest
from app.services.delivery.email import render_digest

CFG = load_config()
NOW = datetime.now(UTC)


def _item(signal_id: int, headline: str, so_what: str, entity: str, score: float) -> dict:
    return {
        "signal_id": signal_id,
        "headline": headline,
        "so_what": so_what,
        "entity": entity,
        "score": score,
    }


@pytest.fixture
def sample_digests():
    return {
        "sales": Digest(
            persona="sales",
            items=[
                _item(1, "Sonatype expands Cargo support", "Lead with registry breadth.", "sonatype", 0.82),
                _item(2, "GitHub raises enterprise pricing", "Expect procurement friction.", "github", 0.71),
            ],
            interrupts=[{"signal_id": 2, "reason": "pricing"}],
            silent_entities=["harbor"],
            generated_at=NOW,
        ),
        "product": Digest(
            persona="product",
            items=[
                _item(3, "Harbor adds SBOM export", "Close the parity gap on supply-chain artifacts.", "harbor", 0.88),
            ],
            interrupts=[],
            silent_entities=["sonatype"],
            generated_at=NOW,
        ),
        "exec": Digest(
            persona="exec",
            items=[
                _item(4, "Market consolidation accelerates", "Board-level narrative on platform bets.", "industry", 0.95),
                _item(5, "Security incident at competitor", "Reinforce trust positioning.", "sonatype", 0.91),
            ],
            interrupts=[{"signal_id": 5, "reason": "security"}],
            silent_entities=[],
            generated_at=NOW,
        ),
    }


@pytest.fixture
def empty_digest():
    return Digest(
        persona="sales",
        items=[],
        interrupts=[],
        silent_entities=["sonatype", "harbor"],
        generated_at=NOW,
    )


@pytest.fixture
def fake_smtp():
    class _FakeSMTP:
        def __init__(self):
            self.sent = 0

        def send(self, **kwargs):
            self.sent += 1

    return _FakeSMTP()


def test_one_template_renders_all_three_personas_differently(sample_digests):
    from app.services.delivery.email import render_digest
    sales = render_digest(sample_digests["sales"], cfg=CFG)
    exec_ = render_digest(sample_digests["exec"], cfg=CFG)
    assert sales.subject != exec_.subject
    assert sales.html != exec_.html

def test_css_is_inlined_because_mail_clients_strip_style_blocks(sample_digests):
    html = render_digest(sample_digests["sales"], cfg=CFG).html
    assert "<style" not in html
    assert "style=" in html

def test_every_item_links_back_into_the_app(sample_digests):
    html = render_digest(sample_digests["sales"], cfg=CFG).html
    assert CFG.delivery.app_base_url in html

def test_an_empty_digest_still_sends_and_reports_stability(empty_digest):
    result = render_digest(empty_digest, cfg=CFG)
    assert "no material" in result.html.lower()

def test_send_records_a_delivery_row_and_never_calls_smtp_in_tests(session, fake_smtp, sample_digests):
    from app.services.delivery.email import send_digest
    send_digest(session, sample_digests["sales"], smtp=fake_smtp, cfg=CFG)
    from app.models.delivery import Delivery
    assert session.query(Delivery).count() == 1
    assert fake_smtp.sent == 1
