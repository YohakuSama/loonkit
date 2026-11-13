#!/usr/bin/env python3
"""Read-only audit of *effective*, ordered LoonKit remote policy boundaries.

The remote URLs in the active manifest are immutable. This script never edits
snapshots, overrides a policy, or assigns a hostname solely from its CDN.
It distinguishes exact duplicates, earlier-suffix shadowing, and intended
priority exceptions. DNS/IP/GeoIP and third-party service ownership still
require runtime validation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from loon_resources import ROOT, content_rules, section, remote_entries


def ancestors(value: str):
    parts = value.lower().split(".")
    for i in range(len(parts)):
        yield ".".join(parts[i:])


def analyze(root: Path = ROOT, *, replacements: dict[str, str] | None = None,
            priority: tuple[str, ...] | None = None) -> dict:
    """Inspect all real subscriptions; optional replacements model a proposed release.

    replacements maps an existing manifest tag to an on-disk candidate file.
    priority, if supplied, lists all tags in effective loading order.
    """
    root = Path(root)
    profile = (root / "LoonKit.lcf").read_text(encoding="utf-8")
    manifest = json.loads((root / "build/release_manifest.json").read_text(encoding="utf-8"))
    subscriptions = remote_entries(profile)
    resources = {item["uri"]: item for item in manifest["runtime_resources"]}
    if {x["uri"] for x in subscriptions} != set(resources):
        raise ValueError("manifest and live remote subscriptions differ")
    replacements = replacements or {}
    tags = [x["tag"] for x in subscriptions]
    if not set(replacements).issubset(tags):
        raise ValueError("replacement refers to unknown live subscription")
    if priority is not None:
        if len(priority) != len(tags) or set(priority) != set(tags):
            raise ValueError("priority must permute every live subscription exactly once")
        subscriptions = sorted(subscriptions, key=lambda x: priority.index(x["tag"]))

    exact = {}
    suffix = {}
    counts = Counter()
    types = Counter()
    per_tag = defaultdict(Counter)
    collisions = Counter()
    examples = defaultdict(list)
    candidate_rule_count = 0

    for record in subscriptions:
        tag = record["tag"]
        policy = record["policy"]
        ref = resources[record["uri"]]
        replacement = replacements.get(tag)
        path = root / (replacement or ref["path"])
        data = path.read_bytes()
        if replacement is None and hashlib.sha256(data).hexdigest() != ref["sha256"]:
            raise ValueError("changed frozen subscription: " + ref["path"])
        rows = content_rules(data)
        if replacement is None and len(rows) != ref["matcher_count"]:
            raise ValueError("matcher count mismatch: " + ref["path"])
        candidate_rule_count += len(rows)
        for text in rows:
            fields = [x.strip() for x in text.split(",")]
            if len(fields) < 2:
                raise ValueError("malformed matcher: " + text[:100])
            kind, value = fields[:2]
            value = value.lower()
            types[kind] += 1
            per_tag[tag]["rules"] += 1
            if kind not in ("DOMAIN", "DOMAIN-SUFFIX"):
                if kind in ("DOMAIN-KEYWORD", "URL-REGEX"):
                    counts["keyword_or_regex"] += 1
                if kind in ("IP-CIDR", "IP-CIDR6") and "no-resolve" not in fields[2:]:
                    counts["ip_may_resolve_dns"] += 1
                continue
            counts["domain_matchers"] += 1
            prior = None
            reason = None
            key = (kind, value)
            if key in exact:
                prior = exact[key]
                reason = "EXACT_DUPLICATE"
            elif kind == "DOMAIN" and ("DOMAIN-SUFFIX", value) in exact:
                prior = exact[("DOMAIN-SUFFIX", value)]
                reason = "SUFFIX_SHADOW"
            if prior is None:
                suffixes = list(ancestors(value))
                start = 0 if kind == "DOMAIN" else 1
                for ancestor in suffixes[start:]:
                    if ancestor in suffix:
                        prior = suffix[ancestor]
                        reason = "SUFFIX_SHADOW"
                        break
            if prior is not None:
                if prior["policy"] == policy:
                    counts["same_policy_redundant"] += 1
                    per_tag[tag]["same_policy_redundant"] += 1
                else:
                    counts["cross_policy_fully_shadowed"] += 1
                    per_tag[tag]["cross_policy_fully_shadowed"] += 1
                    group = (prior["policy"], policy, reason)
                    collisions[group] += 1
                    if len(examples[group]) < 6:
                        examples[group].append({
                            "earlier_tag": prior["tag"], "later_tag": tag,
                            "earlier_rule": prior["rule"], "later_rule": text,
                        })
            now = {"tag": tag, "policy": policy, "rule": text}
            if key not in exact:
                exact[key] = now
            if kind == "DOMAIN-SUFFIX" and value not in suffix:
                suffix[value] = now

    local_rules = [line.strip() for line in section(profile, "Rule").splitlines()
                   if line.strip() and not line.lstrip().startswith("#")]
    if "FINAL,Final" not in local_rules:
        raise ValueError("missing explicit Final fallback")
    return {
        "remote_subscriptions": len(subscriptions),
        "remote_rules": candidate_rule_count,
        "by_matcher_type": dict(sorted(types.items())),
        "summary": dict(sorted(counts.items())),
        "policy_pairs": [
            {"earlier_policy": early, "later_policy": late, "reason": reason,
             "count": count, "examples": examples[(early, late, reason)]}
            for (early, late, reason), count in collisions.most_common()
        ],
        "per_subscription": {key: dict(val) for key, val in per_tag.items()},
        "final_rule": local_rules[-1],
        "geoip_cn_before_final": "GEOIP,CN,DIRECT,no-resolve" in local_rules[:-1],
        "candidate_mode": bool(replacements or priority),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the complete report")
    args = parser.parse_args()
    result = analyze()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({
            "remote_subscriptions": result["remote_subscriptions"],
            "remote_rules": result["remote_rules"],
            "summary": result["summary"],
            "first_20_pairs": result["policy_pairs"][:20],
            "final_rule": result["final_rule"],
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
