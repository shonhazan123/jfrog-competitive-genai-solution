from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.industry_themes import (
    build_industry_item,
    fetch_active_industry_signals,
    list_themes as _list_themes,
    theme_detail as _theme_detail,
)


def list_industry(session: Session, limit: int = 50) -> dict:
    signals = fetch_active_industry_signals(session, limit=limit)
    items = [build_industry_item(session, signal) for signal in signals]
    return {"items": items, "total": len(items), "cursor": None}


def list_themes(session: Session) -> list[dict]:
    return _list_themes(session)


def theme_detail(session: Session, key: str) -> dict:
    return _theme_detail(session, key)
