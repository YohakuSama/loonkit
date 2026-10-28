#!/usr/bin/env python3
"""Check that all StashKit remote rules actually download from the published GitHub Raw URLs.

This is a release-only check: run after merge on main. Unlike a repository tree
check, this catches HTTP errors, bad redirects and stale/raw content.
"""
import concurrent.futures
import hashlib
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "stashkit" / "StashKit.yaml"
PREFIX = "https://raw.githubusercontent.com/YohakuSama/loonkit/main/stashkit/rules/"


def check(item):
    name, spec = item
    url = spec["url"]
    if not url.startswith(PREFIX):
        raise AssertionError(f"{name}: unexpected host/path: {url}")
    basename = url[len(PREFIX):]
    if "/" in basename or not basename.endswith(".txt"):
        raise AssertionError(f"{name}: unsafe asset URL {url}")
    local_path = ROOT / "stashkit" / "rules" / basename
    expected = local_path.read_bytes()
    last_error = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "StashKit-publish-validator/1.0",
                         "Accept": "text/plain,*/*"},
            )
            with urllib.request.urlopen(req, timeout=35) as response:
                if response.status != 200:
                    raise AssertionError(f"HTTP {response.status}: {url}")
                downloaded = response.read()
            if downloaded != expected:
                raise AssertionError(
                    f"{name}: HTTP 200 but content SHA mismatch: "
                    f"local={hashlib.sha256(expected).hexdigest()} "
                    f"remote={hashlib.sha256(downloaded).hexdigest()}"
                )
            return name, len(downloaded)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            last_error = error
            if attempt < 3:
                time.sleep(attempt * 2)
    raise AssertionError(f"{name}: unavailable after 3 attempts: {last_error}")


def main():
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    items = list(config["rule-providers"].items())
    if len(items) != 54:
        raise AssertionError(f"Expected 54 providers, got {len(items)}")
    total_bytes = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(check, item): item[0] for item in items}
        for future in concurrent.futures.as_completed(futures):
            name, size = future.result()
            total_bytes += size
            print(f"PASS: {name} HTTP 200, {size} bytes, exact byte-for-byte match")
    print(f"PASS: all 54 live GitHub Raw URLs verified, {total_bytes:,} total bytes")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise
