import json
from datetime import UTC, datetime

from app.models.registry import Source
from app.services.collection.apis.base import ApiRecord
from app.services.collection.fetcher import Fetcher


def _from_epoch_ms(value) -> datetime | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000, tz=UTC)


class LeverAdapter:
    """Public Lever job-board JSON (api.lever.co/v0/postings/<company>?mode=json).

    Same role as the Greenhouse adapter — `talent_org`, the predictive signal — for the
    competitors on Lever. Sonatype (our most direct competitor) is on Lever, verified
    2026-08-26: the board returns id, text (title), createdAt (epoch ms), hostedUrl, and
    categories.{team,location,commitment}."""

    key = "lever"

    def collect(self, source: Source, fetcher: Fetcher) -> list[ApiRecord]:
        result = fetcher.fetch(source.url)
        if not result.body:
            return []
        postings = json.loads(result.body)
        records: list[ApiRecord] = []
        for post in postings:
            categories = post.get("categories") or {}
            records.append(ApiRecord(
                external_id=str(post["id"]),
                title=post.get("text", ""),
                body=post.get("descriptionPlain") or post.get("text", ""),
                occurred_at=_from_epoch_ms(post.get("createdAt")),
                url=post.get("hostedUrl", source.url),
                signal_type_hint="talent_org",
                extra={
                    "team": categories.get("team", ""),
                    "location": categories.get("location", ""),
                    "commitment": categories.get("commitment", ""),
                },
            ))
        return records
