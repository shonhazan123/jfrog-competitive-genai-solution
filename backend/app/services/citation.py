from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Citation:
    source_name: str
    source_url: str            # live URL — never None on a delivered record
    captured_at: str
    origin: str                # extracted | authored | archive
    archived_url: str | None = None
    grade: str | None = None   # None for authored


@dataclass(frozen=True)
class DeliveryRecord:
    source_name: str
    source_url: str
    fetched_at: datetime
    provenance: str = "extracted"
    reliability_grade: str | None = None
    origin: str | None = None


def citation_to_dict(citation: Citation) -> dict:
    return {
        "source_name": citation.source_name,
        "source_url": citation.source_url,
        "captured_at": citation.captured_at,
        "origin": citation.origin,
        "archived_url": citation.archived_url,
        "grade": citation.grade,
    }


def deliverable(record) -> bool:
    """No assertion reaches a consumer screen without a resolvable origin.
    Authored positions are the one exception and carry origin='authored'."""
    if getattr(record, "origin", None) == "authored":
        return True
    url = getattr(record, "source_url", None)
    return bool(url) and url.startswith("http")


def build_citation(record) -> Citation:
    archived = None
    if getattr(record, "provenance", None) == "archive":
        stamp = record.fetched_at.strftime("%Y%m%d%H%M%S")
        archived = f"https://web.archive.org/web/{stamp}id_/{record.source_url}"
    origin = getattr(record, "origin", None) or getattr(record, "provenance", "extracted")
    return Citation(
        source_name=record.source_name,
        source_url=record.source_url,
        captured_at=record.fetched_at.isoformat(),
        origin=origin,
        archived_url=archived,
        grade=getattr(record, "reliability_grade", None),
    )
