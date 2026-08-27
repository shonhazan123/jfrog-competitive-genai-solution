def test_web_search_maps_client_results_to_hits():
    from agent.tools.web_search import WebSearch, SearchHit

    class FakeClient:
        def run(self, query, k):
            return [{"title": "T", "url": "https://x.com/a", "snippet": "S", "published_at": None}]

    ws = WebSearch(client=FakeClient())
    hits = ws.search("malicious npm package", k=3)
    assert hits == [SearchHit(title="T", url="https://x.com/a", snippet="S", published_at=None)]


def test_web_search_drops_results_without_a_url():
    from agent.tools.web_search import WebSearch

    class FakeClient:
        def run(self, query, k):
            return [{"title": "no url", "url": "", "snippet": "s"}, {"title": "ok", "url": "https://x", "snippet": "s"}]

    hits = WebSearch(client=FakeClient()).search("q")
    assert [h.url for h in hits] == ["https://x"]
