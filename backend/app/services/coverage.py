from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.config.schema import AppConfig
from app.models.registry import Entity, Source

_ADAPTER_HINTS: dict[str, str] = {
    "osv": "security_trust",
}

CellStatus = Literal["multiple", "one", "gap", "not_applicable"]


@dataclass(frozen=True)
class CoverageCell:
    signal_type: str
    status: CellStatus
    source_count: int


@dataclass(frozen=True)
class CoverageRow:
    entity: str
    tier: int | None
    cells: dict[str, CoverageCell]


@dataclass(frozen=True)
class CoverageMatrix:
    columns: list[str]
    rows: list[CoverageRow]
    gap_count: int


def _effective_covers(source: Source, columns: list[str]) -> list[str]:
    if source.covers:
        return [c for c in source.covers if c in columns]

    if source.kind == "html_page" or source.mode == "snapshot":
        return list(columns)

    if source.kind == "api":
        hint = _ADAPTER_HINTS.get(source.adapter or "")
        return [hint] if hint and hint in columns else []

    return []


def _source_contributes(source: Source, signal_type: str, columns: list[str]) -> bool:
    if not source.enabled:
        return False
    if source.robots_allowed is False:
        return False
    return signal_type in _effective_covers(source, columns)


def _cell_status(count: int) -> CellStatus:
    if count >= 2:
        return "multiple"
    if count == 1:
        return "one"
    return "gap"


def build_coverage_matrix(session: Session, cfg: AppConfig | None = None) -> CoverageMatrix:
    if cfg is None:
        from app.config.loader import load_config

        cfg = load_config()

    columns = list(cfg.signal_types.coverage_columns)

    entities = (
        session.query(Entity)
        .filter(Entity.kind.in_(["competitor", "industry"]))
        .order_by(Entity.tier, Entity.slug)
        .all()
    )
    sources = session.query(Source).all()

    rows: list[CoverageRow] = []
    gap_count = 0

    for entity in entities:
        entity_sources = [s for s in sources if s.entity_id == entity.id]
        cells: dict[str, CoverageCell] = {}

        for col in columns:
            count = sum(
                1
                for source in entity_sources
                if _source_contributes(source, col, columns)
            )
            status = _cell_status(count)
            if status == "gap":
                gap_count += 1
            cells[col] = CoverageCell(
                signal_type=col,
                status=status,
                source_count=count,
            )

        rows.append(
            CoverageRow(
                entity=entity.slug,
                tier=entity.tier,
                cells=cells,
            )
        )

    return CoverageMatrix(columns=columns, rows=rows, gap_count=gap_count)
