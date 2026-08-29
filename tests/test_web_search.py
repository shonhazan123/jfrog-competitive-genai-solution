def test_web_search_maps_client_results_to_hits():
    from agent.tools.web_search import WebSearch, SearchHit

    class FakeClient:
        def run(self, query, k):
            return [{"title": "T", "url": "https://x.com/a", "snippet": "S", "published_at": None}]

    ws = WebSearch(client=FakeClient())
    hits = ws.search("malicious npm package", k=3)
    assert hits == [SearchHit(title="T", url="https://x.com/a", snippet="S", published_at=None)]


def test_web_search_strips_nul_and_control_bytes_from_hits():
    from agent.tools.web_search import WebSearch, SearchHit

    class FakeClient:
        def run(self, query, k):
            return [
                {
                    "title": "Aqua\x00Trivy advisory",
                    "url": "https://x.com/a",
                    "snippet": "path-traversal\x00 disclosed\x07",
                    "published_at": None,
                }
            ]

    hits = WebSearch(client=FakeClient()).search("trivy cve", k=3)
    assert hits == [
        SearchHit(
            title="AquaTrivy advisory",
            url="https://x.com/a",
            snippet="path-traversal disclosed",
            published_at=None,
        )
    ]


def test_web_search_drops_results_without_a_url():
    from agent.tools.web_search import WebSearch

    class FakeClient:
        def run(self, query, k):
            return [{"title": "no url", "url": "", "snippet": "s"}, {"title": "ok", "url": "https://x", "snippet": "s"}]

    hits = WebSearch(client=FakeClient()).search("q")
    assert [h.url for h in hits] == ["https://x"]


def test_extract_results_reads_message_output_text_url_citations():
    from agent.tools.web_search import _extract_results

    class UrlCitation:
        type = "url_citation"

        def __init__(self, url, title, start_index, end_index):
            self.url = url
            self.title = title
            self.start_index = start_index
            self.end_index = end_index

    class OutputText:
        type = "output_text"

        def __init__(self):
            self.text = "See npm supply chain report for details."
            self.annotations = [
                UrlCitation(
                    "https://example.com/npm",
                    "NPM Supply Chain Report",
                    4,
                    28,
                ),
                UrlCitation(
                    "https://example.com/other",
                    "Other Source",
                    0,
                    3,
                ),
            ]

    class Message:
        type = "message"
        role = "assistant"

        def __init__(self):
            self.content = [OutputText()]

    class WebSearchCall:
        type = "web_search_call"
        status = "completed"

    class FakeResponse:
        output = [WebSearchCall(), Message()]

    raw = _extract_results(FakeResponse(), k=5)
    assert len(raw) == 2
    assert raw[0]["url"] == "https://example.com/npm"
    assert raw[0]["title"] == "NPM Supply Chain Report"
    assert raw[0]["snippet"] == "npm supply chain report "
