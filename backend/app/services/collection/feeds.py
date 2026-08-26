import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
import feedparser

@dataclass(frozen=True)
class FeedEntry:
    external_id: str
    title: str
    link: str
    published_at: datetime | None
    summary_html: str
    content_html: str | None

def _stable_id(entry, link: str, title: str) -> str:
    """Prefer the feed's own id, then the link, then a hash. Never a random value —
    novelty depends on this being identical across runs."""
    if getattr(entry, "id", None):
        return entry.id
    if link:
        return link
    return hashlib.sha256(f"{title}|{getattr(entry, 'published', '')}".encode()).hexdigest()

def _published(entry) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=UTC)

def parse_feed(body: bytes, source_url: str) -> list[FeedEntry]:
    parsed = feedparser.parse(body)
    entries: list[FeedEntry] = []
    for entry in parsed.entries:
        link = getattr(entry, "link", "") or ""
        title = getattr(entry, "title", "") or ""
        content = None
        if getattr(entry, "content", None):
            content = entry.content[0].get("value")
        entries.append(FeedEntry(
            external_id=_stable_id(entry, link, title),
            title=title, link=link, published_at=_published(entry),
            summary_html=getattr(entry, "summary", "") or "",
            content_html=content,
        ))
    return entries
