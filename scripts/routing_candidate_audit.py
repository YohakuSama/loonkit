#!/usr/bin/env python3
"""Audit byte-preserved routing snapshot and cross-policy domain ownership."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "build/candidates/v7.0.1/candidate_manifest.json"
KINDS = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6", "IP-ASN", "USER-AGENT"}
REMOTE = re.compile(r"^https://raw\.githubusercontent\.com/YohakuSama/loonkit/[a-f0-9]{40}/[^,\s]+, policy=[^,]+, tag=[^,]+, enabled=true$")
IP_KINDS = {"IP-CIDR", "IP-CIDR6", "IP-ASN"}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def rule_lines(data: bytes) -> list[str]:
    return [line.strip() for line in data.decode("utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith(("#", ";", "//"))]

def parse_rule(line: str) -> tuple[str, str]:
    parts = [x.strip() for x in line.split(",")]
    if len(parts) not in (2, 3) or parts[0] not in KINDS or not parts[1]:
        raise ValueError("invalid published rule: " + line)
    if len(parts) == 3 and (parts[0] not in IP_KINDS or parts[2] != "no-resolve"):
        raise ValueError("invalid rule parameter: " + line)
    return parts[0], parts[1].lower()

def section(data: str, name: str) -> str:
    match = re.search(r"(?m)^\[" + re.escape(name) + r"\]$", data)
    if not match:
        raise ValueError("missing section: " + name)
    next_section = re.search(r"(?m)^\[[^]]+\]$", data[match.end():])
    return data[match.end(): match.end() + next_section.start() if next_section else None]

def audit() -> dict:
    manifest = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    baseline = (ROOT / manifest["baseline_profile"]).read_bytes()
    if sha256(baseline) != manifest["baseline_profile_sha256"]:
        raise ValueError("immutable base profile changed")
    old = baseline.decode("utf-8")
    candidate = (ROOT / manifest["preview_profile"]).read_text(encoding="utf-8")
    original = manifest["baseline_resources"]
    newer = manifest["candidate_resources"]
    if len(original) != len(newer) or len(newer) != manifest["runtime_resource_count"]:
        raise ValueError("unexpected resource inventory")
    if not candidate.startswith("# LoonKit " + manifest["version"] + "\n"):
        raise ValueError("candidate version differs")
    if section(old, "General") != section(candidate, "General"):
        raise ValueError("general settings changed")
    for part in ("Proxy", "Remote Proxy", "Remote Filter", "Proxy Group", "Host", "Rule", "Plugin"):
        if section(old, part) != section(candidate, part):
            raise ValueError("runtime directive changed: " + part)
    expected = old.replace("# LoonKit " + manifest["base_version"] + "\n",
                           "# LoonKit " + manifest["version"] + "\n", 1)
    all_rules = []
    checked = 0
    for former, row in zip(original, newer):
        for field in ("tag", "policy", "enabled", "sha256", "matcher_count"):
            if former[field] != row[field]:
                raise ValueError("changed ownership or rule content: " + field)
        if row["commit"] != manifest["asset_commit"] or not row["path"].startswith("rules/releases/" + manifest["version"] + "/"):
            raise ValueError("mixed candidate resource identity")
        before = (ROOT / former["path"]).read_bytes()
        after = (ROOT / row["path"]).read_bytes()
        if before != after or sha256(after) != row["sha256"]:
            raise ValueError("rule content changed: " + row["tag"])
        rules = rule_lines(after)
        if len(rules) != row["matcher_count"]:
            raise ValueError("matcher count drift: " + row["tag"])
        for r in rules:
            kind, value = parse_rule(r)
            all_rules.append((kind, value, row["policy"], row["tag"]))
        checked += len(rules)
        expected = expected.replace(former["uri"], row["uri"], 1)
    if checked != manifest["remote_rule_count"] or candidate != expected:
        raise ValueError("candidate not byte-equivalent to production routing")
    configured = [s.strip() for s in section(candidate, "Remote Rule").splitlines()
                  if s.strip() and not s.lstrip().startswith(("#", ";"))]
    if len(configured) != len(newer) or not all(REMOTE.fullmatch(x) for x in configured):
        raise ValueError("unsupported or missing subscription directives")
    if configured != [r["uri"] + ", policy=" + r["policy"] + ", tag=" + r["tag"] + ", enabled=true"
                      for r in newer]:
        raise ValueError("candidate subscription order differs")
    suffixes = defaultdict(set)
    exact = defaultdict(set)
    duplicates = Counter()
    for kind, value, policy, tag in all_rules:
        duplicates[(kind, value, policy)] += 1
        if kind == "DOMAIN-SUFFIX":
            suffixes[value].add(policy)
        elif kind == "DOMAIN":
            exact[value].add(policy)
    collisions = Counter()
    examples = {}
    for kind, value, policy, tag in all_rules:
        if kind not in ("DOMAIN", "DOMAIN-SUFFIX"):
            continue
        labels = value.split(".")
        other_policies = set()
        for idx in range(len(labels)):
            other_policies.update(suffixes.get(".".join(labels[idx:]), ()))
        if kind == "DOMAIN-SUFFIX":
            other_policies.update(exact.get(value, ()))
        for other in other_policies - {policy}:
            key = tuple(sorted((policy, other)))
            collisions[key] += 1
            examples.setdefault(key, (tag, kind + "," + value))
    return {
        "candidate": manifest["version"],
        "resource_count": len(newer),
        "matcher_count": checked,
        "exact_same_policy_duplicates": sum(n-1 for n in duplicates.values() if n>1),
        "cross_policy_domain_overlap": [
            {"policies": list(key), "overlap_hits": count, "example": list(examples[key])}
            for key, count in collisions.most_common(30)
        ],
        "invariant": "identical rule bytes, policy and subscription order",
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
