#!/usr/bin/env python3
"""Lossless, same-subscription rule subsumption audit for frozen Loon rules.

Never change source rules during audit. The only removable predicate is a
predicate wholly contained by another predicate of the SAME remote subscription
and SAME effective policy. No cross-policy first-match reorder or keyword
substitution. Existing frozen files are immutable, new candidates go elsewhere.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import ipaddress
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAIN_KINDS = {"DOMAIN", "DOMAIN-SUFFIX"}
IP_KINDS = {"IP-CIDR", "IP-CIDR6"}


def rule_fields(line: str) -> tuple[str, str, tuple[str, ...]]:
    parts = [value.strip() for value in line.split(",")]
    if len(parts) < 2 or any(not value for value in parts):
        raise ValueError("malformed rule " + line[:120])
    return parts[0], parts[1].lower(), tuple(parts[2:])


def ancestors(domain: str):
    parts = domain.split(".")
    for offset in range(len(parts)):
        yield ".".join(parts[offset:])


def trim_rules(raw: bytes) -> tuple[bytes, dict, list[dict]]:
    text = raw.decode("utf-8")
    if text.encode("utf-8") != raw:
        raise ValueError("unexpected text encoding")
    lines = text.splitlines(keepends=True)
    suffix = set()
    exact = set()
    ips = defaultdict(set)
    entries = []
    for index, original in enumerate(lines):
        line = original.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        kind, value, flags = rule_fields(line)
        key = (kind, value, flags)
        entries.append((index, line, key))
        if kind == "DOMAIN-SUFFIX":
            suffix.add((value, flags))
        elif kind == "DOMAIN":
            exact.add((value, flags))
        elif kind in IP_KINDS:
            net = ipaddress.ip_network(value, strict=False)
            if ((net.version == 6) != (kind == "IP-CIDR6")):
                raise ValueError("invalid IP family: " + line)
            ips[(kind, flags)].add(net)
    seen = set()
    removed = []
    for index, line, key in entries:
        kind, value, flags = key
        reason = None
        if key in seen:
            reason = "EXACT_DUPLICATE"
        elif kind in DOMAIN_KINDS:
            parents = tuple(ancestors(value))
            if kind == "DOMAIN":
                if any((ancestor, flags) in suffix for ancestor in parents):
                    reason = "DOMAIN_COVERED_BY_SUFFIX"
            elif any((ancestor, flags) in suffix for ancestor in parents[1:]):
                reason = "SUFFIX_COVERED_BY_PARENT"
        elif kind in IP_KINDS:
            network = ipaddress.ip_network(value, strict=False)
            current = network
            available = ips[(kind, flags)]
            while current.prefixlen:
                current = current.supernet()
                if current in available:
                    reason = "IP_SUBNET_COVERED_BY_PARENT"
                    break
        if reason:
            removed.append({"line": index + 1, "rule": line, "reason": reason})
        else:
            seen.add(key)
    omit = {record["line"] - 1 for record in removed}
    optimized = "".join(s for index, s in enumerate(lines) if index not in omit).encode("utf-8")
    if len(entries) - len(removed) != sum(
        bool(s.strip()) and not s.lstrip().startswith(("#", ";", "//"))
        for s in optimized.decode("utf-8").splitlines()
    ):
        raise AssertionError("rule count changed unexpectedly")
    return optimized, {
        "before": len(entries), "after": len(entries) - len(removed),
        "removed": len(removed), "bytes_before": len(raw),
        "bytes_after": len(optimized),
        "reasons": dict(sorted(Counter(r["reason"] for r in removed).items())),
        "original_sha256": hashlib.sha256(raw).hexdigest(),
        "optimized_sha256": hashlib.sha256(optimized).hexdigest(),
    }, removed


def audit(root: Path = ROOT, *, write_dir: str | None = None) -> dict:
    manifest = json.loads((root / "build/release_manifest.json").read_text(encoding="utf-8"))
    records = manifest["runtime_resources"]
    result = {}
    samples = {}
    counts = Counter()
    totals = Counter()
    for row in records:
        path = root / row["path"]
        source = path.read_bytes()
        if hashlib.sha256(source).hexdigest() != row["sha256"]:
            raise ValueError("unverified input bytes: " + row["path"])
        dest, summary, removed = trim_rules(source)
        if summary["before"] != row["matcher_count"]:
            raise ValueError("manifest count mismatch: " + row["path"])
        if summary["removed"] and write_dir:
            target = root / write_dir / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(dest)
        elif write_dir:
            target = root / write_dir / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source)
        result[row["tag"]] = {"source": row["path"], "policy": row["policy"], **summary}
        samples[row["tag"]] = removed[:3]
        counts.update(summary["reasons"])
        totals.update({"before": summary["before"], "after": summary["after"],
                       "removed": summary["removed"], "bytes_before": summary["bytes_before"],
                       "bytes_after": summary["bytes_after"]})
    report = {"algorithm": "same_subscription_equivalent_subsumption_v1",
              "version": manifest["label"], "sources": len(records),
              "totals": dict(totals), "reasons": dict(counts),
              "resources": result, "examples": samples}
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audit", action="store_true", help="read-only coverage audit")
    p.add_argument("--write-dir", default=None, help="only emit a new candidate directory")
    p.add_argument("--report", default=None)
    args = p.parse_args()
    if not args.audit and not args.write_dir:
        p.error("select --audit or --write-dir")
    report = audit(write_dir=args.write_dir)
    output = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
    if args.report:
        Path(args.report).write_text(output + "\n", encoding="utf-8")
    print(json.dumps({"version": report["version"], "totals": report["totals"],
                      "reasons": report["reasons"],
                      "top": sorted(((k, v["removed"], v["bytes_before"] - v["bytes_after"])
                                     for k, v in report["resources"].items()),
                                    key=lambda x: x[1], reverse=True)[:15]},
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
