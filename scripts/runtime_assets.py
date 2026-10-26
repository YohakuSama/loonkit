#!/usr/bin/env python3
"""Read-only verification of the complete static Loon runtime dependency graph."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
from urllib.request import urlopen

from loon_resources import ROOT, pinned_uri as pinned, remote_entries, section

LOCK = "build/runtime.lock.json"
MAX_BYTES = 8 * 1024 * 1024
MAX_RESOURCES = 256
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
SCRIPT = re.compile(r"\bscript\(\s*([\"'])([^\"']+)\1\s*,")
ICON = re.compile(r"\bimg[-_]url\s*=\s*([^,\s]+)")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("invalid runtime asset path")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or ".." in Path(relative).parts:
        raise ValueError("runtime asset escapes repository")
    return path


def profile_dependencies(profile: str) -> list[tuple[str, str]]:
    result = [(r["uri"], "rule") for r in remote_entries(profile)]
    for line in section(profile, "Proxy Group").splitlines():
        if line.lstrip().startswith(("#", ";", "//")):
            continue
        result.extend((m[1], "icon") for m in ICON.finditer(line))
    for line in section(profile, "Plugin").splitlines():
        if not line.strip() or line.lstrip().startswith(("#", ";", "//")):
            continue
        parts = [p.strip() for p in line.split(",")]
        if parts[1:] != ["enabled=true"]:
            raise ValueError("invalid public plugin declaration")
        result.append((parts[0], "plugin"))
    return result


def plugin_dependencies(plugin: str) -> list[tuple[str, str]]:
    headings = re.findall(r"(?m)^\[([^\]]+)\]$", plugin)
    if len(headings) != len(set(headings)) or set(headings) - {"Argument", "Script"}:
        raise ValueError("plugin section requires an explicit dependency parser")
    result = [(m[1], "icon") for m in re.finditer(r"(?m)^#!icon\s*=\s*(\S+)\s*$", plugin)]
    for line in section(plugin, "Script").splitlines():
        if not line.strip() or line.lstrip().startswith(("#", ";", "//")):
            continue
        matches = list(SCRIPT.finditer(line))
        if len(matches) != 1:
            raise ValueError("unsupported plugin script declaration")
        result.append((matches[0][2], "script"))
        result.extend((m[1], "icon") for m in ICON.finditer(line)
                      if m[1].startswith(("http:", "https:")))
    return result


def build_lock(root: Path = ROOT, *, aliases: dict[str, str] | None = None) -> dict:
    """Explicit maintainer operation; checks never regenerate this evidence."""
    root = Path(root)
    previous = json.loads((root / LOCK).read_text()) if (root / LOCK).is_file() else {}
    locations = {r["uri"]: r["local_path"] for r in previous.get("resources", [])}
    locations.update(aliases or {})
    pending = profile_dependencies((root / "LoonKit.lcf").read_text())
    resources = {}
    while pending:
        uri, kind = pending.pop(0)
        reference = pinned(uri)
        if uri in resources:
            if resources[uri]["kind"] != kind:
                raise ValueError("runtime asset has conflicting roles")
            continue
        relative = locations.get(uri, reference["path"])
        raw = local_file(root, relative).read_bytes()
        if not raw or len(raw) > MAX_BYTES or len(resources) >= MAX_RESOURCES:
            raise ValueError("empty or excessive runtime assets")
        resources[uri] = {**reference, "kind": kind, "local_path": relative, "sha256": digest(raw)}
        if kind == "plugin":
            pending.extend(plugin_dependencies(raw.decode("utf-8")))
    return {"schema_version": 1, "resources": [resources[u] for u in sorted(resources)]}


def check(root: Path = ROOT, *, remote: bool = False) -> dict:
    root = Path(root)
    lock = json.loads((root / LOCK).read_text())
    if set(lock) != {"schema_version", "resources"} or lock["schema_version"] != 1:
        raise ValueError("unknown runtime lock schema")
    rows = lock["resources"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_RESOURCES:
        raise ValueError("runtime lock inventory is missing or excessive")
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"uri", "commit", "path", "kind", "local_path", "sha256"}
                or not DIGEST.fullmatch(str(row["sha256"]))):
            raise ValueError("invalid runtime lock record")
        if {k: row[k] for k in ("uri", "commit", "path")} != pinned(row["uri"]):
            raise ValueError("runtime lock identity differs from immutable URL")
        local_file(root, row["local_path"])
    if len({r["uri"] for r in rows}) != len(rows):
        raise ValueError("duplicate runtime asset")
    # Traverse actual profile/plugin bytes, rather than trusting the lock's list.
    if build_lock(root) != lock:
        raise ValueError("runtime graph, asset bytes or locked inventory differ")
    if remote:
        def verify(row):
            with urlopen(row["uri"], timeout=35) as response:
                if response.geturl() != row["uri"]:
                    raise ValueError("immutable runtime asset redirected")
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES or digest(raw) != row["sha256"]:
                raise ValueError("remote runtime asset differs: " + row["path"])
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(verify, rows))
    return {"assets": len(rows), "remote_checked": remote}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--check", action="store_true")
    operation.add_argument("--write", action="store_true")
    parser.add_argument("--remote", action="store_true")
    args = parser.parse_args()
    if args.write:
        if args.remote:
            parser.error("--remote requires --check")
        (ROOT / LOCK).write_text(json.dumps(build_lock(), ensure_ascii=False, indent=2) + "\n")
    else:
        print(json.dumps(check(remote=args.remote), sort_keys=True))
