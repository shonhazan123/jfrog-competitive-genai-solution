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


def _extract_results(resp, k: int) -> list[dict]:
    results: list[dict] = []
    for item in getattr(resp, "output", []) or []:
        for citation in getattr(item, "annotations", []) or []:
            url = getattr(citation, "url", "") or ""
            if url:
                results.append({
                    "title": getattr(citation, "title", "") or url,
                    "url": url,
                    "snippet": getattr(citation, "text", "") or "",
                    "published_at": None,
                })
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
