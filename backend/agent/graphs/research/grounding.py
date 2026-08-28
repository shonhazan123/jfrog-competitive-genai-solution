from __future__ import annotations


def hit_urls(material) -> set[str] | None:
    """Return search-hit URLs when material is web-search hits; None for structured sources."""
    if material is None:
        return set()
    urls: set[str] = set()
    saw_search_hit = False
    for item in material:
        url = getattr(item, "url", None)
        if url:
            saw_search_hit = True
            urls.add(url)
    return urls if saw_search_hit else None


def source_url_grounded(source_url: str, material) -> bool:
    urls = hit_urls(material)
    if urls is None:
        return True
    return bool(source_url) and source_url in urls
