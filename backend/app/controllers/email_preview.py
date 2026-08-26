from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.controllers.digests import exec_weekly
from app.controllers.signals import list_signals
from app.serializers.common import fmt_ts
from app.services.delivery.assembly import assemble


def _email_items_from_signals(items: list[dict]) -> list[dict]:
    email_items = []
    for item in items:
        email_items.append(
            {
                "signal_type": item["signal_type"],
                "headline": item["headline"],
                "so_what": item.get("so_what") or "",
                "flag": "⚠ caution" if item.get("handling") == "caution" else None,
                "app_link": f"https://app.internal/signals/{item['id']}",
            }
        )
    return email_items


def _persona_preview(session: Session, persona: str) -> dict:
    cfg = load_config()
    digest = assemble(session, persona, cfg, datetime.now(UTC))
    signal_list = list_signals(session, persona=persona)
    # A digest is persona-ranked: order by the persona's own score so each
    # audience leads with what matters to them, not by recency.
    ranked = sorted(signal_list["items"], key=lambda item: item.get("score", 0.0), reverse=True)
    items = _email_items_from_signals(ranked) or [
        {
            "signal_type": "product_capability",
            "headline": item["headline"],
            "so_what": item.get("so_what") or "",
            "flag": None,
            "app_link": f"https://app.internal/signals/{item['signal_id']}",
        }
        for item in digest.items
    ]
    caution_count = sum(1 for item in signal_list["items"] if item.get("handling") == "caution")
    return {
        "persona": persona,
        "from_name": "CI System",
        "from_email": "ci-digest@example.internal",
        "subject": f"Competitive digest — {persona.title()} · Tue 26 Aug",
        "meta": f"{len(items)} items · {caution_count} handling caution · budget capped",
        "lead": "Digest items assembled from the ledger with evidence attached.",
        "items": items,
        "sent_at": fmt_ts(datetime(2026, 8, 26, 6, 5, tzinfo=UTC)),
        "delivery_logged": True,
        "footer": (
            "Every item links to its evidence in the app. Unsubscribe or change cadence in Settings. "
            "Sent by the scheduler at 06:05 · delivery logged."
        ),
    }


def _exec_preview(session: Session) -> dict:
    weekly = exec_weekly(session)
    items = []
    for trend in weekly["trends"]:
        direction_symbol = {"toward_us": "↑ toward us", "against_us": "↑ against us", "lateral": "→ lateral"}
        items.append(
            {
                "signal_type": f"trend {direction_symbol.get(trend['direction'], '→ lateral')}",
                "headline": trend["title"],
                "so_what": trend["body"],
                "flag": None,
                "app_link": f"https://app.internal/exec/{trend['id']}",
            }
        )
    for stability in weekly["stability"]:
        items.append(
            {
                "signal_type": "stability",
                "headline": stability["title"],
                "so_what": stability["detail"],
                "flag": "stable",
                "app_link": "https://app.internal/exec/stability",
            }
        )
    return {
        "persona": "exec",
        "from_name": "CI System",
        "from_email": "ci-digest@example.internal",
        "subject": weekly["subject"],
        "meta": f"{len(items)} items · weekly · stability reported",
        "lead": weekly["lead"],
        "items": items,
        "sent_at": fmt_ts(datetime(2026, 8, 28, 16, 5, tzinfo=UTC)),
        "delivery_logged": True,
        "footer": (
            "Every item links to its evidence in the app. Unsubscribe or change cadence in Settings. "
            "Sent by the scheduler · delivery logged."
        ),
    }


def preview(session: Session, persona: str = "sales") -> dict:
    """Return the fixture-shaped envelope (sales/product/exec) for shape tests."""
    return {
        "sales": _persona_preview(session, "sales"),
        "product": _persona_preview(session, "product"),
        "exec": _exec_preview(session),
    }
