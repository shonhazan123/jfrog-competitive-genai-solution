from rapidfuzz import fuzz
from app.config.schema import ClusterConfig
from app.services.normalization.clean import normalize_text

GRADE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}

def cluster_key(facets: dict, window_days: int) -> tuple:
    bucket = facets["occurred_at"].toordinal() // window_days
    return (facets["entity"], frozenset(facets.get("capability_tags", [])), bucket)

def _representative_rank(item: dict) -> tuple:
    """Evidentiary ordering: source grade, then primary standing, then recency.
    The same ordering the retrieval rerank uses."""
    return (GRADE_RANK.get(item.get("reliability_grade", "F"), 9),
            0 if item.get("is_primary") else 1,
            -item["occurred_at"].timestamp())

def cluster(items: list[dict], cfg: ClusterConfig) -> list[list[dict]]:
    """Group items describing one real-world event. Runs AFTER classification —
    two articles about different things can share a headline."""
    buckets: dict[tuple, list[dict]] = {}
    for entry in items:
        buckets.setdefault(cluster_key(entry, cfg.window_days), []).append(entry)

    clusters: list[list[dict]] = []
    for bucket in buckets.values():
        remaining = list(bucket)
        while remaining:
            seed = remaining.pop(0)
            group = [seed]
            changed = True
            while changed:
                changed = False
                still: list[dict] = []
                for candidate in remaining:
                    if any(
                        fuzz.partial_token_set_ratio(
                            normalize_text(member["headline"]),
                            normalize_text(candidate["headline"]),
                        ) >= cfg.title_similarity
                        for member in group
                    ):
                        group.append(candidate)
                        changed = True
                    else:
                        still.append(candidate)
                remaining = still
            group.sort(key=_representative_rank)
            clusters.append(group)
    return clusters
