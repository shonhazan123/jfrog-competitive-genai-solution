from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.capture import PageSnapshot, RawCapture
from app.models.ledger import Claim, ClaimVersion, Evidence
from app.models.registry import Entity, Source
from app.services.collection.fetcher import Fetcher
from app.services.detection.hashing import content_hash, normalized_hash
from app.services.detection.structural_diff import diff_rows
from app.services.normalization.parsers.html_dom import parse_html
from app.services.normalization.tracked_page import ComparisonRow, extract_comparison_rows

@dataclass
class SnapshotReport:
    captures: int = 0
    claims_created: int = 0
    versions_created: int = 0

def _store_blob(digest: str, body: bytes) -> str:
    from app.settings import settings
    path = Path(settings.blob_dir) / f"{digest}.bin"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return str(path)

def _rows_from(body: bytes) -> list[ComparisonRow]:
    return extract_comparison_rows(parse_html(body.decode("utf-8", errors="replace")))

def _ingest_page(
    session: Session,
    source: Source,
    jfrog: Entity,
    body: bytes,
    fetched_at: datetime,
    http_status: int,
    provenance: str,
    previous: list[ComparisonRow],
    report: SnapshotReport,
) -> list[ComparisonRow]:
    """Store one page version and diff it against the previous one. This is the whole
    snapshot pipeline for a single capture: parse the tracked comparison page into rows,
    persist the version, and turn any material row change into a claim update."""
    digest = content_hash(body)
    text = body.decode("utf-8", errors="replace")
    capture = RawCapture(
        source_id=source.id, fetched_at=fetched_at, http_status=http_status,
        content_hash=digest, blob_path=_store_blob(digest, body),
        extracted_text=text, provenance=provenance,
    )
    session.add(capture)
    session.flush()
    report.captures += 1

    rows = _rows_from(body)
    session.add(PageSnapshot(
        source_id=source.id, capture_id=capture.id, captured_at=fetched_at,
        text_hash=normalized_hash(text),
        rows=[{"dimension": r.dimension, "cells": r.cells} for r in rows],
    ))

    for change in diff_rows(previous, rows):
        if change.kind == "cosmetic":
            continue
        _apply(session, source, jfrog, fetched_at, change, capture, report)
    return rows

def _last_snapshot(session: Session, source_id: int) -> PageSnapshot | None:
    return (
        session.query(PageSnapshot)
        .filter_by(source_id=source_id)
        .order_by(PageSnapshot.captured_at.desc())
        .first()
    )

def collect_snapshot_source(session: Session, source: Source, fetcher: Fetcher) -> int:
    """Fetch a tracked comparison page once, now, and run the extraction/diff pipeline
    against the most recent stored version. A live change to the page extends the same
    claim history. Returns the number of captures created (0 if the page is unchanged)."""
    result = fetcher.fetch(source.url, source.etag)
    if result.not_modified or not result.body:
        return 0

    last = _last_snapshot(session, source.id)
    if last is not None and last.text_hash == normalized_hash(
        result.body.decode("utf-8", errors="replace")
    ):
        return 0  # identical to the last stored version — nothing changed

    jfrog = session.query(Entity).filter_by(slug="jfrog").one()
    previous = (
        [ComparisonRow(dimension=r["dimension"], cells=r["cells"]) for r in last.rows]
        if last is not None else []
    )
    report = SnapshotReport()
    _ingest_page(
        session, source, jfrog, result.body, datetime.now(UTC),
        result.status, "live", previous, report,
    )
    if result.etag:
        source.etag = result.etag
    return report.captures

def _apply(session, source, jfrog, at, change, capture, report):
    """Create or update the claim this change refers to, and record its version."""
    dimension_claim = (
        session.query(Claim)
        .filter_by(dimension=change.dimension, asserting_entity_id=source.entity_id,
                   subject_entity_id=jfrog.id)
        .one_or_none()
    )
    if dimension_claim is None:
        dimension_claim = Claim(
            subject_entity_id=jfrog.id, asserting_entity_id=source.entity_id,
            claim_text=change.new_value or "", claim_type="positioning",
            capability_tags=[], dimension=change.dimension,
            reliability_grade=source.reliability_grade, first_seen_at=at, last_confirmed_at=at,
        )
        session.add(dimension_claim)
        session.flush()
        report.claims_created += 1
    else:
        dimension_claim.claim_text = change.new_value or dimension_claim.claim_text
        dimension_claim.last_confirmed_at = at

    if change.old_value is not None:
        session.add(ClaimVersion(
            claim_id=dimension_claim.id, old_text=change.old_value,
            new_text=change.new_value, change_kind=change.kind, changed_at=at,
        ))
        report.versions_created += 1

    if change.new_value:
        offset = capture.extracted_text.find(change.new_value)
        if offset >= 0:
            session.add(Evidence(
                claim_id=dimension_claim.id, capture_id=capture.id,
                quote=capture.extracted_text[offset:offset + len(change.new_value)],
                quote_offset=offset,
            ))
    return report.claims_created, report.versions_created
