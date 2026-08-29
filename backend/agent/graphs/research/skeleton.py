from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Protocol, TypedDict

from agent.log import get_logger, step

logger = get_logger("agent.research")

DEFAULT_MAX_WORKERS = int(os.environ.get("RESEARCH_MAX_WORKERS", "4"))


class ResearchState(TypedDict):
    targets: list[dict]
    cursor: int
    attempts: int
    drafts: list[dict]
    max_attempts: int


class ResearchDeps(Protocol):
    max_attempts: int

    def plan(self) -> list[dict]: ...
    def collect(self, target: dict) -> object | None: ...
    def search(self, target: dict, *, attempt: int = 1) -> object: ...
    def assess(self, target: dict, material: object, attempts: int) -> tuple[str, dict | None]: ...
    def absent_draft(self, target: dict) -> dict: ...


def _target_identity(target: dict) -> str:
    for key in ("name", "key", "id", "competitor"):
        if key in target:
            return str(target[key])
    return repr(target)


def _resolve_one(deps: ResearchDeps, target: dict, max_attempts: int) -> dict:
    """Resolve one target to a draft (filled) or absent draft, bounded by max_attempts."""
    try:
        material = deps.collect(target)
        attempts = 0
        if material is None:
            material = deps.search(target, attempt=1)
            attempts = 1
        while True:
            verdict, draft = deps.assess(target, material, attempts)
            if verdict == "resolved" and draft is not None:
                return draft
            if verdict == "absent" or attempts >= max_attempts:
                return deps.absent_draft(target)
            if isinstance(material, list) and len(material) == 0:
                return deps.absent_draft(target)
            material = deps.search(target, attempt=attempts + 1)
            attempts += 1
    except Exception as exc:
        logger.warning(
            "research.target.failed target=%s error=%s",
            _target_identity(target),
            exc,
        )
        return deps.absent_draft(target)


def run_research(
    deps: ResearchDeps,
    *,
    max_workers: int | None = None,
    progress=None,
) -> list[dict]:
    if progress is None:
        def progress(*_args, **_kwargs):
            return None

    targets = deps.plan()
    step(logger, "research.plan", targets=len(targets))
    progress("plan", 0, len(targets))
    if not targets:
        return []

    workers = DEFAULT_MAX_WORKERS if max_workers is None else max_workers
    pool_size = min(workers, len(targets))
    drafts: list[dict | None] = [None] * len(targets)

    def _job(index: int, target: dict) -> tuple[int, dict]:
        return index, _resolve_one(deps, target, deps.max_attempts)

    completed = 0
    with ThreadPoolExecutor(max_workers=pool_size) as pool:
        future_targets = {
            pool.submit(_job, i, target): (i, target)
            for i, target in enumerate(targets)
        }
        for future in as_completed(future_targets):
            index, target = future_targets[future]
            try:
                resolved_index, draft = future.result()
                drafts[resolved_index] = draft
            except Exception as exc:
                logger.warning(
                    "research.target.failed target=%s error=%s",
                    _target_identity(target),
                    exc,
                )
                drafts[index] = deps.absent_draft(target)
            completed += 1
            progress("research", completed, len(targets))

    return [d for d in drafts if d is not None]
