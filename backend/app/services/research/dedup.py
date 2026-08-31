from __future__ import annotations

from rapidfuzz import fuzz

from app.config.schema import ClusterConfig
from app.services.normalization.clean import normalize_text


def dedupe_items(items: list[dict], cfg: ClusterConfig) -> list[list[dict]]:
    """Group research items that describe one real-world event, so N framings of
    the same story (from N search hits) become one signal instead of N.

    Buckets by ``(entity_slug, signal_type, time-window)`` — signal_type rather
    than the LLM-assigned capability_tags, which vary across duplicate framings
    and would wrongly split a cluster. Within a bucket, items whose normalized
    headlines score ``>= title_similarity`` (rapidfuzz ``token_set_ratio``) are
    merged. ``token_set_ratio`` (not the ``partial_`` variant) is used because
    research headlines are full sentences: the partial variant scores two
    different events that merely share an entity name ("Vista acquires Sonatype"
    vs "Sonatype launches SBOM tool") as a match, whereas the full set ratio only
    fires on genuinely near-identical headlines. Each returned group is ordered
    most-recent-first, so ``group[0]`` is the representative; ``len(group)`` is
    the corroboration count.
    """
    buckets: dict[tuple, list[dict]] = {}
    for item in items:
        bucket = item["occurred_at"].toordinal() // cfg.window_days
        key = (item["entity_slug"], item["signal_type"], bucket)
        buckets.setdefault(key, []).append(item)

    groups: list[list[dict]] = []
    for bucket_items in buckets.values():
        remaining = list(bucket_items)
        while remaining:
            group = [remaining.pop(0)]
            changed = True
            while changed:
                changed = False
                still: list[dict] = []
                for candidate in remaining:
                    if any(
                        fuzz.token_set_ratio(
                            normalize_text(member["headline"]),
                            normalize_text(candidate["headline"]),
                        )
                        >= cfg.title_similarity
                        for member in group
                    ):
                        group.append(candidate)
                        changed = True
                    else:
                        still.append(candidate)
                remaining = still
            group.sort(key=lambda it: -it["occurred_at"].timestamp())
            groups.append(group)
    return groups
