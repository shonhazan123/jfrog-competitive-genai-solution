"""Shared query helpers for research agents."""

from __future__ import annotations

# Ruling: attempt 2/3 append fixed broadening suffixes (not verbatim retries).
_BROADEN_BY_ATTEMPT: dict[int, str] = {
    2: " overview OR review OR capabilities",
    3: " alternative OR comparison OR documentation",
}


def dedupe_names(name: str, aliases: list[str]) -> list[str]:
    """Return name + aliases with case-insensitive duplicates removed."""
    seen: set[str] = set()
    out: list[str] = []
    for item in [name, *aliases]:
        text = (item or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def broaden_query(base: str, attempt: int) -> str:
    if attempt <= 1:
        return base
    return base + _BROADEN_BY_ATTEMPT.get(attempt, _BROADEN_BY_ATTEMPT[3])
