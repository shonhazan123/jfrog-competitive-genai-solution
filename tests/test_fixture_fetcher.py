import json
from pathlib import Path

import pytest

from app.services.collection.fetcher import FetchResult
from app.services.collection.fixture_fetcher import FixtureFetcher


def test_fetch_returns_fixture_bytes(tmp_path: Path) -> None:
    body = b"<html>fixture</html>"
    filename = "abc123.bin"
    (tmp_path / filename).write_bytes(body)
    manifest = {"https://example.com/page": filename}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    result = FixtureFetcher(tmp_path).fetch("https://example.com/page")

    assert result == FetchResult(
        url="https://example.com/page",
        status=200,
        body=body,
        etag=None,
        last_modified=None,
        not_modified=False,
    )


def test_fetch_unknown_url_raises_lookup_error(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text("{}")

    with pytest.raises(LookupError, match="No fixture for"):
        FixtureFetcher(tmp_path).fetch("https://example.com/missing")
