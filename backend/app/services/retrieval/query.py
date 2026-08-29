from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text

from app.services.retrieval.rerank import rerank_scores


@dataclass(frozen=True)
class Hit:
    chunk_id: int
    record_type: str
    record_id: int
    text: str
    score: float
    source_id: int
    reliability_grade: str
    url: str | None = None


def _build_prefilter(filters: dict, preset: str, rcfg) -> tuple[str, dict] | None:
    clauses = ["record_type = ANY(:record_types)"]
    params: dict = {"record_types": rcfg.presets[preset]["record_types"]}

    if "entity_ids" in filters:
        entity_ids = filters["entity_ids"]
        if not entity_ids:
            return None
        clauses.append("entity_id = ANY(:entity_ids)")
        params["entity_ids"] = entity_ids

    return " AND ".join(clauses), params


def _row_to_dict(row) -> dict:
    return {
        "id": row.id,
        "record_type": row.record_type,
        "record_id": row.record_id,
        "text": row.text,
        "source_id": row.source_id,
        "reliability_grade": row.reliability_grade,
        "url": row.url,
    }


def _lexical_candidates(session, *, query: str, where_clause: str, params: dict, limit: int) -> list[dict]:
    sql = text(
        f"""
        SELECT id, record_type, record_id, text, source_id, reliability_grade, url,
               ts_rank(tsv, plainto_tsquery('english', :query)) AS rank_score
        FROM chunk
        WHERE {where_clause}
          AND tsv @@ plainto_tsquery('english', :query)
        ORDER BY rank_score DESC
        LIMIT :limit
        """
    )
    rows = session.execute(sql, {**params, "query": query, "limit": limit}).all()
    return [_row_to_dict(row) for row in rows]


def _format_vector(vec: list[float]) -> str:
    return "[" + ",".join(str(v) for v in vec) + "]"


def _semantic_candidates(
    session, *, query: str, where_clause: str, params: dict, limit: int, qvec: list[float], hnsw_ef_search: int
) -> list[dict]:
    # Postgres SET does not accept bind parameters; inline the integer (guarded
    # by int()) instead of passing it as a query parameter.
    session.execute(text(f"SET LOCAL hnsw.ef_search = {int(hnsw_ef_search)}"))
    sql = text(
        f"""
        SELECT id, record_type, record_id, text, source_id, reliability_grade, url,
               (embedding <=> CAST(:qvec AS vector)) AS distance
        FROM chunk
        WHERE {where_clause}
          AND embedding IS NOT NULL
        ORDER BY distance ASC
        LIMIT :limit
        """
    )
    rows = session.execute(
        sql,
        {**params, "query": query, "limit": limit, "qvec": _format_vector(qvec)},
    ).all()
    return [_row_to_dict(row) for row in rows]


def _rrf_fuse(rank_lists: list[list[dict]], rrf_k: int) -> tuple[dict[int, float], dict[int, dict]]:
    scores: dict[int, float] = {}
    chunk_map: dict[int, dict] = {}
    for candidates in rank_lists:
        for rank, row in enumerate(candidates, start=1):
            chunk_id = row["id"]
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
            chunk_map.setdefault(chunk_id, row)
    return scores, chunk_map


def _apply_diversity_cap(hits: list[Hit], max_per_document: int) -> list[Hit]:
    counts: dict[int, int] = {}
    kept: list[Hit] = []
    for hit in hits:
        seen = counts.get(hit.record_id, 0)
        if seen < max_per_document:
            kept.append(hit)
            counts[hit.record_id] = seen + 1
    return kept


def _to_hits(scored: list[tuple[dict, float]]) -> list[Hit]:
    return [
        Hit(
            chunk_id=row["id"],
            record_type=row["record_type"],
            record_id=row["record_id"],
            text=row["text"],
            score=score,
            source_id=row["source_id"] or 0,
            reliability_grade=row["reliability_grade"] or "",
            url=row.get("url"),
        )
        for row, score in scored
    ]


def search(
    session,
    *,
    query: str,
    preset: str,
    filters: dict,
    cfg=None,
    embedder=None,
) -> list[Hit]:
    if cfg is None or cfg is ...:
        from app.config.loader import load_config

        cfg = load_config()

    rcfg = cfg.retrieval
    prefilter = _build_prefilter(filters, preset, rcfg)
    if prefilter is None:
        return []

    where_clause, params = prefilter
    rank_lists = [
        _lexical_candidates(
            session,
            query=query,
            where_clause=where_clause,
            params=params,
            limit=rcfg.candidate_pool,
        )
    ]

    if embedder is not None:
        qvec = embedder.embed([query])[0]
        rank_lists.append(
            _semantic_candidates(
                session,
                query=query,
                where_clause=where_clause,
                params=params,
                limit=rcfg.candidate_pool,
                qvec=qvec,
                hnsw_ef_search=rcfg.hnsw_ef_search,
            )
        )

    rrf_scores, chunk_map = _rrf_fuse(rank_lists, rcfg.rrf_k)
    if not rrf_scores:
        return []

    scored = rerank_scores(rrf_scores, chunk_map, rcfg)
    hits = _to_hits(scored)
    return _apply_diversity_cap(hits, rcfg.max_per_document)
