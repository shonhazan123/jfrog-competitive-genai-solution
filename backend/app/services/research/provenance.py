from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from agent.llm import get_embedder
from app.models.capture import RawCapture
from app.models.registry import Source
from app.services.ingestion.embedding import index_chunks

# PostgreSQL text/varchar columns reject NUL (0x00). Web-search results — and the
# LLM syntheses derived from them — occasionally carry NUL or other C0 control
# bytes; strip them (keeping tab/newline/carriage-return) before anything is
# written to the database.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_text(value):
    """Remove NUL and other disallowed control characters from a string.

    Non-strings pass through unchanged so callers can apply it defensively.
    """
    if not isinstance(value, str):
        return value
    return _CONTROL_CHARS.sub("", value)


def agent_source(session: Session, agent_key: str, reliability_grade: str = "C") -> Source:
    key = f"{agent_key}_research"
    source = session.query(Source).filter_by(key=key).one_or_none()
    if source is None:
        source = Source(
            key=key, entity_id=None, url=f"internal://{key}", kind="api", mode="api",
            reliability_grade=reliability_grade, is_primary=False, check_frequency_minutes=1440,
        )
        session.add(source)
        session.flush()
    return source


def record_finding(session: Session, agent_key: str, url: str, text: str,
                   reliability_grade: str = "C") -> RawCapture:
    source = agent_source(session, agent_key, reliability_grade)
    url = sanitize_text(url)
    text = sanitize_text(text)
    capture = RawCapture(
        source_id=source.id, fetched_at=datetime.now(UTC), http_status=200,
        content_hash=hashlib.sha256((url + text).encode()).hexdigest(),
        blob_path=url, extracted_text=text, provenance="web_search",
    )
    session.add(capture)
    session.flush()
    return capture


def index_finding(session: Session, *, record_type: str, record_id: int, text: str,
                  entity_id, signal_type, published_at, reliability_grade,
                  url: str | None = None) -> int:
    text = sanitize_text(text)
    return index_chunks(
        session, [{"text": text, "prefix": None, "section_path": [], "token_count": 0}],
        record_type=record_type, record_id=record_id, embedder=get_embedder(),
        entity_id=entity_id, signal_type=signal_type,
        published_at=published_at, reliability_grade=reliability_grade, url=url,
    )
