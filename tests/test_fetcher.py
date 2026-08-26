import httpx, pytest
from app.services.collection.fetcher import StaticFetcher, BrowserFetcher
from app.services.collection.robots import RobotsCache

def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))

def test_conditional_get_reports_not_modified():
    def handler(request):
        assert request.headers["If-None-Match"] == 'W/"abc"'
        return httpx.Response(304)
    result = StaticFetcher(client=_client(handler)).fetch("https://x.test/p", etag='W/"abc"')
    assert result.not_modified is True
    assert result.body is None

def test_successful_fetch_captures_etag_and_body():
    def handler(request):
        return httpx.Response(200, content=b"<html>hi</html>", headers={"ETag": 'W/"z"'})
    result = StaticFetcher(client=_client(handler)).fetch("https://x.test/p")
    assert result.status == 200
    assert result.body == b"<html>hi</html>"
    assert result.etag == 'W/"z"'

def test_sends_identifying_user_agent():
    seen = {}
    def handler(request):
        seen["ua"] = request.headers["User-Agent"]
        return httpx.Response(200, content=b"")
    StaticFetcher(client=_client(handler)).fetch("https://x.test/p")
    assert "jfrog-ci-bot" in seen["ua"]

def test_robots_disallow_is_respected():
    def handler(request):
        return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
    cache = RobotsCache(client=_client(handler))
    assert cache.allowed("https://x.test/public") is True
    assert cache.allowed("https://x.test/private/page") is False

def test_browser_fetcher_fails_loudly():
    with pytest.raises(NotImplementedError, match="browser rendering"):
        BrowserFetcher().fetch("https://x.test/p")
