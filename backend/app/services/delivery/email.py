from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import css_inline
import jinja2
from sqlalchemy.orm import Session

from app.config.schema import AppConfig
from app.models.delivery import Delivery, DigestRun
from app.services.delivery.assembly import Digest

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(_TEMPLATES_DIR))

_SUBJECT_BY_PERSONA = {
    "sales": "Sales competitive digest — today's signals",
    "product": "Product competitive digest — today's signals",
    "exec": "Executive briefing — competitive landscape",
}


@dataclass
class RenderedDigest:
    subject: str
    html: str


def _subject_for(persona: str) -> str:
    return _SUBJECT_BY_PERSONA.get(
        persona,
        f"Competitive digest — {persona.title()}",
    )


def render_digest(digest: Digest, cfg: AppConfig) -> RenderedDigest:
    template = _ENV.get_template("digest.html.j2")
    html = template.render(
        persona=digest.persona,
        items=digest.items,
        interrupts=digest.interrupts,
        silent_entities=digest.silent_entities,
        generated_at=digest.generated_at,
        app_base_url=cfg.delivery.app_base_url,
    )
    inlined_html = css_inline.inline(html)
    return RenderedDigest(subject=_subject_for(digest.persona), html=inlined_html)


def send_digest(
    session: Session,
    digest: Digest,
    smtp: object,
    cfg: AppConfig,
) -> None:
    rendered = render_digest(digest, cfg)

    digest_run = DigestRun(
        persona=digest.persona,
        generated_at=digest.generated_at,
        item_count=len(digest.items),
    )
    session.add(digest_run)
    session.flush()

    recipients = cfg.delivery.recipients.get(digest.persona) or [
        "ci-digest@example.internal"
    ]

    smtp.send(subject=rendered.subject, html=rendered.html, to=recipients)

    delivery = Delivery(
        digest_run_id=digest_run.id,
        recipient=", ".join(recipients),
        sent_at=datetime.now(UTC),
        status="sent",
    )
    session.add(delivery)
    session.flush()
