from datetime import UTC, datetime, timedelta

import pytest

from app.config.loader import load_config
from app.models.registry import Entity, Source
from app.models.signal import Signal

CFG = load_config()


@pytest.fixture
def capturing_smtp():
    """Records the recipient list and message the demo digest would send."""

    class _Capturing:
        def __init__(self):
            self.calls = []

        def send(self, subject: str, html: str, to: list[str]) -> None:
            self.calls.append({"subject": subject, "html": html, "to": to})

    return _Capturing()


def _seed(session) -> None:
    """Two competitor entities, a source each, and signals: two security_trust
    (different dates) plus one non-security signal that must not appear in news."""
    sonatype = Entity(slug="sonatype", name="Sonatype", kind="competitor", tier=1)
    github = Entity(slug="github", name="GitHub", kind="competitor", tier=1)
    session.add_all([sonatype, github])
    session.flush()

    now = datetime.now(UTC)
    for entity in (sonatype, github):
        source = Source(
            key=f"{entity.slug}_src",
            entity_id=entity.id,
            url=f"https://example.com/{entity.slug}",
            kind="atom",
            mode="feed",
            reliability_grade="A",
            is_primary=True,
            check_frequency_minutes=60,
            last_checked_at=now,
        )
        session.add(source)
        session.flush()
        entity._src_id = source.id  # type: ignore[attr-defined]

    rows = [
        (sonatype, "security_trust", "Old CVE in Nexus", now - timedelta(days=5)),
        (github, "security_trust", "Fresh RCE in Actions", now - timedelta(days=1)),
        (sonatype, "positioning_messaging", "Sonatype rebrands", now),
        (github, "product_capability", "GitHub ships SBOM export", now),
        (sonatype, "talent_org", "Sonatype hiring 20 security engineers", now),
    ]
    for entity, signal_type, headline, occurred_at in rows:
        session.add(
            Signal(
                source_id=entity._src_id,
                entity_id=entity.id,
                signal_type=signal_type,
                headline=headline,
                occurred_at=occurred_at,
                cluster_key=f"c-{headline}",
                score_sales=80.0,
                score_product=80.0,
                score_exec=80.0,
                so_what_sales="Lead with it.",
                status="active",
            )
        )
    session.flush()


def test_demo_items_lead_with_a_feature_and_a_hiring_signal(session):
    from app.services.delivery.assembly import select_demo_items

    _seed(session)
    items = select_demo_items(session, "sales", limit=3)
    types = {i["headline"] for i in items}

    # feature + hiring are guaranteed; security is excluded (it has its own section)
    assert "GitHub ships SBOM export" in types
    assert "Sonatype hiring 20 security engineers" in types
    assert "Old CVE in Nexus" not in types
    assert "Fresh RCE in Actions" not in types


def test_newest_security_news_returns_only_security_newest_first(session):
    from app.services.delivery.assembly import newest_security_news

    _seed(session)
    news = newest_security_news(session, limit=3)

    headlines = [n["headline"] for n in news]
    assert "Sonatype rebrands" not in headlines  # non-security excluded
    assert headlines == ["Fresh RCE in Actions", "Old CVE in Nexus"]  # newest first


def test_run_demo_digest_emails_the_given_address(session, capturing_smtp):
    from worker.jobs import run_demo_digest

    _seed(session)
    result = run_demo_digest(
        session=session, to_email="me@example.com", smtp=capturing_smtp, cfg=CFG
    )

    html = capturing_smtp.calls[0]["html"]
    assert len(capturing_smtp.calls) == 1
    assert capturing_smtp.calls[0]["to"] == ["me@example.com"]
    # main section leads with feature + hiring; security appears in its own section
    assert "GitHub ships SBOM export" in html
    assert "Sonatype hiring 20 security engineers" in html
    assert "Fresh RCE in Actions" in html  # security news section
    assert result["recipient"] == "me@example.com"
    assert result["item_count"] <= 3

    from app.models.delivery import Delivery

    delivery = session.query(Delivery).one()
    assert delivery.recipient == "me@example.com"
    assert delivery.status == "sent"


def test_controller_rejects_an_invalid_email(session):
    from app.controllers.digests import send_demo_digest

    result = send_demo_digest(session, "not-an-email")
    assert result["status"] == "invalid_email"


def test_controller_reports_not_configured_when_credentials_missing(
    session, monkeypatch
):
    from app.controllers.digests import send_demo_digest

    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_APP_PASSWORD", raising=False)
    _seed(session)

    result = send_demo_digest(session, "me@example.com")
    assert result["status"] == "not_configured"
    assert "SMTP_USER" in result["detail"]
