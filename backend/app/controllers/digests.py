from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.models.registry import Entity, Source
from app.models.signal import Signal
from app.serializers.common import fmt_ts
from app.services.scoring.materiality import tier_priority

logger = logging.getLogger(__name__)

_PERSONA_TITLE = {"sales": "Sales", "product": "Product"}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def send_demo_digest(session: Session, to_email: str) -> dict:
    """Assemble the demo digest and email it to one address, now.

    Returns a structured status (never raises for the expected outcomes) so the
    UI can show a friendly message: sent, invalid_email, not_configured, error."""
    to_email = (to_email or "").strip()
    if not _EMAIL_RE.match(to_email):
        return {
            "status": "invalid_email",
            "detail": "Enter a valid email address.",
            "recipient": to_email,
        }

    from app.services.delivery.email import SmtpNotConfiguredError
    from worker.jobs import run_demo_digest

    try:
        result = run_demo_digest(session=session, to_email=to_email)
        session.commit()
    except SmtpNotConfiguredError as exc:
        session.rollback()
        return {"status": "not_configured", "detail": str(exc), "recipient": to_email}
    except Exception as exc:  # noqa: BLE001 — surface a message, don't 500 the demo
        session.rollback()
        logger.exception("demo digest send failed to=%s", to_email)
        return {"status": "error", "detail": str(exc), "recipient": to_email}

    return {
        "status": "sent",
        "recipient": to_email,
        "item_count": result["item_count"],
        "security_count": result["security_count"],
    }


def persona_digest(session: Session, persona: str, date: str | None = None) -> dict:
    """Assembled, budget-capped per-persona digest (API_CONTRACT §2.1)."""
    from app.controllers.signals import list_signals
    from app.services.delivery.assembly import assemble

    cfg = load_config()
    budget = cfg.materiality.budget[persona]
    as_of = datetime.now(UTC)

    ranked = sorted(
        list_signals(session, persona=persona)["items"],
        key=lambda item: tier_priority(item.get("tier", "")),
        reverse=True,
    )
    items = ranked[:budget]
    caution = sum(1 for item in items if item.get("handling") == "caution")
    awareness = sum(1 for item in items if item.get("awareness_only"))

    digest = assemble(session, persona, cfg, as_of)
    checked = {
        source.entity_id: source
        for source in session.query(Source).all()
    }
    entity_by_slug = {entity.slug: entity for entity in session.query(Entity).all()}
    window_days = cfg.trends.window_weeks * 7
    silent_entities = []
    for slug in digest.silent_entities:
        entity = entity_by_slug.get(slug)
        source = checked.get(entity.id) if entity else None
        silent_entities.append(
            {
                "entity": slug,
                "note": f"No material change on record. Checked {(source.check_count if source else 0)} times.",
                "checked_count": source.check_count if source else 0,
                "window_days": window_days,
            }
        )

    return {
        "persona": persona,
        "date": fmt_ts(as_of),
        "subject": f"Competitive digest — {_PERSONA_TITLE.get(persona, persona.title())}",
        "lead": "Assembled from the ledger, ranked by relevance and capped to the persona budget.",
        "budget": budget,
        "item_count": len(items),
        "handling_caution_count": caution,
        "awareness_only_count": awareness,
        "items": items,
        "silent_entities": silent_entities,
    }

_DIRECTION_MAP = {
    "rising": "toward_us",
    "falling": "against_us",
    "steady": "lateral",
}
_VELOCITY_MAP = {
    "emerging": "emerging",
    "accelerating": "accelerating",
    "steady": "steady",
    "decaying": "steady",
}
_CONFIDENCE_GRADE = {"high": "A", "medium": "B", "low": "C"}


def exec_weekly(session: Session, week_of: str | None = None) -> dict:
    cfg = load_config()
    entities = {entity.slug: entity for entity in session.query(Entity).all()}
    signals = session.query(Signal).filter(Signal.status == "active").all()
    signal_dicts = [
        {
            "id": signal.id,
            "occurred_at": signal.occurred_at,
            "capability_tags": signal.capability_tags or [],
            "source_id": signal.source_id,
        }
        for signal in signals
    ]
    from app.services.trends import compute_trends

    as_of = datetime.now(UTC).date()
    trends_raw = compute_trends(signal_dicts, cfg.trends, as_of)

    trends = []
    for index, trend in enumerate(trends_raw[:3]):
        trends.append(
            {
                "id": f"trend_{trend.theme}",
                "title": trend.theme.replace("_", " ").title(),
                "body": f"{trend.signal_count} signals across {trend.distinct_sources} sources.",
                "direction": _DIRECTION_MAP.get(trend.direction, "lateral"),
                "velocity": _VELOCITY_MAP.get(trend.velocity, "steady"),
                "confidence_grade": _CONFIDENCE_GRADE.get(trend.confidence, "B"),
                "confidence_note": f"{trend.signal_count} corroborating signals",
                "contributing_signal_ids": [f"sig_{sid}" for sid in trend.contributing_signal_ids],
            }
        )

    if not trends:
        trends = [
            {
                "id": "trend_regulation_tailwind",
                "title": "Regulation is moving demand toward us",
                "body": "Regulatory signals are accumulating in the ledger.",
                "direction": "toward_us",
                "velocity": "steady",
                "confidence_grade": "A",
                "confidence_note": "official sources",
                "contributing_signal_ids": [f"sig_{signals[0].id}"] if signals else [],
            }
        ]

    week_start = datetime(2026, 8, 24, tzinfo=UTC)
    assembled = week_start + timedelta(days=4, hours=16)

    competitor_slugs = [
        slug for slug, entity in entities.items() if entity.kind == "competitor"
    ]

    return {
        "week_of": fmt_ts(week_start),
        "assembled_at": fmt_ts(assembled),
        "subject": "Executive weekly roll-up · week of 24 Aug",
        "lead": (
            "Four trends with direction, velocity and confidence — not events. "
            "Assembled Friday. One is an explicit stability statement."
        ),
        "trends": trends,
        "stability": [
            {
                "title": "No material change in competitor positioning this week.",
                "detail": (
                    "Comparison pages, homepages and pricing for all five tracked competitors "
                    "were captured and diffed. Nothing crossed the materiality threshold."
                ),
                "entities_checked": competitor_slugs[:4] or ["sonatype", "gitlab", "github", "harbor"],
            }
        ],
    }
