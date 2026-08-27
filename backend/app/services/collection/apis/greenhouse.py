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


class GreenhouseAdapter:
    """Public Greenhouse job-board JSON (boards-api.greenhouse.io/v1/boards/<token>/jobs).

    `talent_org` is the only *predictive* signal type in the model: a hiring surge in a
    capability area is roadmap intelligence 6-12 months before the feature ships. No auth,
    no scraping — a structured public endpoint, the highest quality-to-effort tier."""

    key = "greenhouse"

    def collect(self, source: Source, fetcher: Fetcher) -> list[ApiRecord]:
        result = fetcher.fetch(source.url)
        if not result.body:
            return []
        payload = json.loads(result.body)
        records: list[ApiRecord] = []
        for job in payload.get("jobs", []):
            location = (job.get("location") or {}).get("name", "")
            records.append(ApiRecord(
                external_id=str(job["id"]),
                title=job.get("title", ""),
                body=job.get("content", "") or job.get("title", ""),
                occurred_at=_parse(job.get("updated_at") or job.get("first_published")),
                url=job.get("absolute_url", source.url),
                signal_type_hint="talent_org",
                extra={"location": location},
            ))
        return records
