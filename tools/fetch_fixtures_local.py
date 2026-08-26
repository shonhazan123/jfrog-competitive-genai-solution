#!/usr/bin/env python3
"""Fetch Internet Archive fixtures on the host (outside Docker) for offline replay.

Builds manifest keys byte-for-byte identical to backend/app/services/collection/wayback.py:
  CDX_ENDPOINT + ?url={quote(url, safe='')} + &output=json&limit=60&collapse=digest&filter=statuscode:200
  RAW_PREFIX/{YYYYMMDDHHMMSS}id_/{original_url}
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
RAW_PREFIX = "https://web.archive.org/web"
DEFAULT_LIMIT = 60
USER_AGENT = "jfrog-ci-bot/0.1 (+contact: shonhazan19955@gmail.com)"
REQUEST_TIMEOUT = 30
SLEEP_SECONDS = 1.0
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 2.0

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_YAML = REPO_ROOT / "config" / "sources.yaml"
FIXTURES_DIR = REPO_ROOT / "fixtures" / "wayback"


def build_cdx_query(url: str, limit: int = DEFAULT_LIMIT) -> str:
    """Match wayback.list_snapshots query string exactly."""
    return (
        f"{CDX_ENDPOINT}?url={quote(url, safe='')}"
        f"&output=json&limit={limit}&collapse=digest&filter=statuscode:200"
    )


def build_raw_url(timestamp: str, original_url: str) -> str:
    """Match Snapshot.raw_url format exactly."""
    return f"{RAW_PREFIX}/{timestamp}id_/{original_url}"


def filename_for(url: str) -> str:
    return f"{hashlib.sha256(url.encode()).hexdigest()[:16]}.bin"


def parse_snapshot_sources(path: Path) -> list[tuple[str, str]]:
    """Return (key, url) for each source with mode: snapshot."""
    text = path.read_text(encoding="utf-8")
    sources: list[tuple[str, str]] = []
    blocks = re.split(r"\n\s*-\s+key:\s+", text)
    for block in blocks[1:]:
        key_match = re.match(r"(\S+)", block)
        if not key_match:
            continue
        key = key_match.group(1)
        url_match = re.search(r"^\s*url:\s+(\S+)", block, re.MULTILINE)
        mode_match = re.search(r"^\s*mode:\s+(\S+)", block, re.MULTILINE)
        if url_match and mode_match and mode_match.group(1) == "snapshot":
            sources.append((key, url_match.group(1)))
    return sources


def fetch_bytes(url: str) -> bytes:
    last_exc: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt < MAX_ATTEMPTS:
                print(f"  retry {attempt}/{MAX_ATTEMPTS} for {url}: {exc!r}")
                time.sleep(BACKOFF_SECONDS)
    assert last_exc is not None
    raise last_exc


def save_fixture(manifest: dict[str, str], url: str, body: bytes) -> str:
    name = filename_for(url)
    (FIXTURES_DIR / name).write_bytes(body)
    manifest[url] = name
    return name


def fetch_source(key: str, url: str, manifest: dict[str, str]) -> int:
    cdx_query = build_cdx_query(url)
    print(f"Fetching CDX for {key} ...")
    cdx_body = fetch_bytes(cdx_query)
    save_fixture(manifest, cdx_query, cdx_body)
    time.sleep(SLEEP_SECONDS)

    rows = json.loads(cdx_body.decode("utf-8"))
    snapshot_count = 0
    for row in rows[1:]:
        timestamp = row[1]
        original = row[2]
        raw_url = build_raw_url(timestamp, original)
        print(f"  snapshot {timestamp} -> {original}")
        raw_body = fetch_bytes(raw_url)
        save_fixture(manifest, raw_url, raw_body)
        snapshot_count += 1
        time.sleep(SLEEP_SECONDS)

    return snapshot_count


def main() -> int:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    override_url = sys.argv[1] if len(sys.argv) > 1 else None
    sources = parse_snapshot_sources(SOURCES_YAML)
    if not sources:
        print("No snapshot-mode sources found in config/sources.yaml", file=sys.stderr)
        return 1

    manifest: dict[str, str] = {}
    summaries: list[tuple[str, int]] = []

    for key, config_url in sources:
        url = override_url or config_url
        count = fetch_source(key, url, manifest)
        summaries.append((key, count))

    manifest_path = FIXTURES_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    total_files = len(manifest)
    print()
    for key, count in summaries:
        print(f"{key}: {count} snapshots")
    print(f"total fixture files: {total_files}")
    print(f"fixtures written to {FIXTURES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
