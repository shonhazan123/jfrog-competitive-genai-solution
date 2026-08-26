import json
from datetime import datetime
from app.models.registry import Source
from app.services.collection.apis.base import ApiRecord
from app.services.collection.fetcher import Fetcher

_METRICS = {"C:H": 2.0, "I:H": 2.0, "A:H": 2.0, "PR:N": 1.5, "AV:N": 2.0, "UI:N": 1.5}

def _cvss_from_vector(severity: list[dict]) -> float:
    """OSV supplies a CVSS vector string, not a number. Derive an approximate base
    score for the interrupt rule; exact scoring is a roadmap item."""
    for entry in severity or []:
        vector = entry.get("score", "")
        if vector.startswith("CVSS:"):
            return min(10.0, sum(w for token, w in _METRICS.items() if token in vector))
    return 0.0

class OsvAdapter:
    key = "osv"

    def collect(self, source: Source, fetcher: Fetcher) -> list[ApiRecord]:
        result = fetcher.fetch(source.url)
        if not result.body:
            return []
        payload = json.loads(result.body)
        records: list[ApiRecord] = []
        for vuln in payload.get("vulns", []):
            published = vuln.get("published")
            records.append(ApiRecord(
                external_id=vuln["id"],
                title=vuln.get("summary") or vuln["id"],
                body=vuln.get("details", ""),
                occurred_at=datetime.fromisoformat(published.replace("Z", "+00:00")) if published else None,
                url=next((r["url"] for r in vuln.get("references", [])), f"https://osv.dev/{vuln['id']}"),
                signal_type_hint="security_trust",
                extra={"cvss": _cvss_from_vector(vuln.get("severity", []))},
            ))
        return records
