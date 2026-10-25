"""Dependency-free Loon profile and pinned-resource parsing shared by all channels."""
from __future__ import annotations
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
URI = re.compile(r"https://raw\.githubusercontent\.com/YohakuSama/loonkit/(?P<sha>[a-f0-9]{40})/(?P<path>[A-Za-z0-9_./-]+)\Z")


def section(profile: str, name: str) -> str:
    hit = re.search(r"(?m)^\[" + re.escape(name) + r"\]$", profile)
    if not hit:
        raise ValueError("missing Loon section: " + name)
    text = profile[hit.end():]
    tail = re.search(r"(?m)^\[[^\]]+\]$", text)
    return text[:tail.start()] if tail else text


def remote_entries(profile: str) -> list[dict]:
    result = []
    for line in section(profile, "Remote Rule").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        uri, *flags = [x.strip() for x in line.split(",")]
        match = URI.fullmatch(uri)
        if not match or ".." in match["path"].split("/"):
            raise ValueError("remote rules must use reviewed repository commit URLs")
        options = dict(x.split("=", 1) for x in flags if "=" in x)
        if len(options) != len(flags) or options.get("enabled") != "true":
            raise ValueError("invalid or disabled public beta resource")
        if not options.get("policy") or not options.get("tag"):
            raise ValueError("resource lacks policy or tag")
        result.append({"uri": uri, "commit": match["sha"], "path": match["path"], **options})
    if len({r["tag"] for r in result}) != len(result):
        raise ValueError("duplicate remote resource tag")
    return result


def content_rules(raw: bytes) -> list[str]:
    return [r.strip() for r in raw.decode("utf-8").splitlines()
            if r.strip() and not r.lstrip().startswith(("#", ";", "//"))]
