from __future__ import annotations

from dataclasses import dataclass

from agent.log import get_logger, step

logger = get_logger("agent.web_search")


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str
    published_at: str | None = None


class _OpenAIWebSearchClient:
    """Wraps the OpenAI hosted web_search tool via the Responses API. Verify the
    installed langchain-openai / openai version exposes it before relying on this
    (see Global Constraints: dependency policy)."""

    def __init__(self, model: str = "gpt-4o-mini"):
        from openai import OpenAI

        self._client = OpenAI()
        self._model = model

    def run(self, query: str, k: int) -> list[dict]:
        resp = self._client.responses.create(
            model=self._model,
            tools=[{"type": "web_search"}],
            input=f"Search the web and return the {k} most relevant results for: {query}",
        )
        # Normalised below; shape-mapping kept in one place so the graph never
        # sees vendor payloads.
        return _extract_results(resp, k)


def _annotation_type(annotation) -> str | None:
    ann_type = getattr(annotation, "type", None)
    if ann_type is None and isinstance(annotation, dict):
        ann_type = annotation.get("type")
    return ann_type


def _annotation_field(annotation, field: str, default=""):
    value = getattr(annotation, field, None)
    if value is None and isinstance(annotation, dict):
        value = annotation.get(field)
    return value if value is not None else default


def _content_parts(item) -> list:
    content = getattr(item, "content", None)
    if content is None and isinstance(item, dict):
        content = item.get("content")
    return list(content or [])


def _extract_results(resp, k: int) -> list[dict]:
    """Walk Responses API output: message → output_text → url_citation annotations."""
    results: list[dict] = []
    seen: set[str] = set()

    def add(url: str, title: str = "", snippet: str = "") -> None:
        if not url or url in seen:
            return
        seen.add(url)
        results.append({
            "title": title or url,
            "url": url,
            "snippet": snippet,
            "published_at": None,
        })

    for item in getattr(resp, "output", []) or []:
        item_type = getattr(item, "type", None)
        if item_type is None and isinstance(item, dict):
            item_type = item.get("type")

        if item_type == "web_search_call":
            action = getattr(item, "action", None)
            if action is None and isinstance(item, dict):
                action = item.get("action")
            for source in getattr(action, "sources", None) or []:
                url = getattr(source, "url", "") or ""
                title = getattr(source, "title", "") or ""
                add(url, title)
            continue

        if item_type != "message":
            continue

        for part in _content_parts(item):
            part_type = getattr(part, "type", None)
            if part_type is None and isinstance(part, dict):
                part_type = part.get("type")
            if part_type != "output_text":
                continue

            text = getattr(part, "text", "") or ""
            if not text and isinstance(part, dict):
                text = part.get("text", "") or ""

            annotations = getattr(part, "annotations", None)
            if annotations is None and isinstance(part, dict):
                annotations = part.get("annotations")
            for annotation in annotations or []:
                if _annotation_type(annotation) != "url_citation":
                    continue
                url = _annotation_field(annotation, "url")
                title = _annotation_field(annotation, "title", url)
                start = _annotation_field(annotation, "start_index", None)
                end = _annotation_field(annotation, "end_index", None)
                snippet = ""
                if text and start is not None and end is not None:
                    snippet = text[int(start):int(end)]
                add(url, title, snippet)

    return results[:k]


class WebSearch:
    def __init__(self, client=None):
        self._client = client or _OpenAIWebSearchClient()

    def search(self, query: str, k: int = 5) -> list[SearchHit]:
        raw = self._client.run(query, k)
        hits = [
            SearchHit(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
                published_at=r.get("published_at"),
            )
            for r in raw
            if r.get("url")
        ]
        step(logger, "web_search.done", query=query, hits=len(hits))
        return hits


def web_search(query: str, k: int = 5) -> list[SearchHit]:
    return WebSearch().search(query, k)
