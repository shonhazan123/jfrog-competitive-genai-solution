import json
from datetime import datetime

from app.models.registry import Source
from app.services.collection.apis.base import ApiRecord
from app.services.collection.fetcher import Fetcher


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


class HackerNewsAdapter:
    """Hacker News via the free Algolia search API (hn.algolia.com/api/v1/search_by_date).

    This is the 'what do developers actually say' source — the honest, ToS-clean substitute
    for scraping review sites. The query encodes the subject (e.g. query=Sonatype+Nexus), so
    the same adapter collects sentiment symmetrically about JFrog and every competitor. No
    auth. Comments are often stronger signal than the story itself."""

    key = "hn"

    def collect(self, source: Source, fetcher: Fetcher) -> list[ApiRecord]:
        result = fetcher.fetch(source.url)
        if not result.body:
            return []
        payload = json.loads(result.body)
        records: list[ApiRecord] = []
        for hit in payload.get("hits", []):
            object_id = hit.get("objectID")
            if not object_id:
                continue
            title = hit.get("title") or hit.get("story_title") or ""
            body = hit.get("story_text") or hit.get("comment_text") or title
            records.append(ApiRecord(
                external_id=object_id,
                title=title,
                body=body,
                occurred_at=_parse(hit.get("created_at")),
                url=hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}",
                signal_type_hint=None,  # interpret classifies; HN spans many signal types
                extra={"points": hit.get("points", 0), "num_comments": hit.get("num_comments", 0)},
            ))
        return records
