from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.capture import PageSnapshot, RawCapture
from app.models.ledger import Claim, ClaimVersion, Evidence
from app.models.registry import Entity, Source
from app.services.collection.fetcher import Fetcher
from app.services.collection.wayback import list_snapshots
from app.services.detection.hashing import content_hash, normalized_hash
from app.services.detection.structural_diff import diff_rows
from app.services.normalization.parsers.html_dom import parse_html
from app.services.normalization.tracked_page import ComparisonRow, extract_comparison_rows
from app.settings import settings

@dataclass
class BackfillReport:
    captures: int = 0
    claims_created: int = 0
    versions_created: int = 0

def _store_blob(digest: str, body: bytes) -> str:
    path = Path(settings.blob_dir) / f"{digest}.bin"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return str(path)

def _rows_from(body: bytes) -> list[ComparisonRow]:
    return extract_comparison_rows(parse_html(body.decode("utf-8", errors="replace")))

def backfill_source(session: Session, source: Source, fetcher: Fetcher) -> BackfillReport:
    """Replay every archived version of a tracked page through the live pipeline."""
    report = BackfillReport()
    jfrog = session.query(Entity).filter_by(slug="jfrog").one()
    previous: list[ComparisonRow] = []

    for snapshot in list_snapshots(source.url, fetcher):
        result = fetcher.fetch(snapshot.raw_url)
        if not result.body:
            continue

        digest = content_hash(result.body)
        text = result.body.decode("utf-8", errors="replace")
        capture = RawCapture(
            source_id=source.id, fetched_at=snapshot.timestamp, http_status=result.status,
            content_hash=digest, blob_path=_store_blob(digest, result.body),
            extracted_text=text, provenance="archive",
        )
        session.add(capture)
        session.flush()
        report.captures += 1

        rows = _rows_from(result.body)
        session.add(PageSnapshot(
            source_id=source.id, capture_id=capture.id, captured_at=snapshot.timestamp,
            text_hash=normalized_hash(text),
            rows=[{"dimension": r.dimension, "cells": r.cells} for r in rows],
        ))

        for change in diff_rows(previous, rows):
            if change.kind == "cosmetic":
                continue
            report.claims_created, report.versions_created = _apply(
                session, source, jfrog, snapshot.timestamp, change, capture, report
            )
        previous = rows

    session.commit()
    return report

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
