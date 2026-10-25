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



class PriorPolicyIndex:
    """Only predicates from strictly earlier subscriptions of this same policy."""

    def __init__(self):
        self.exact = set()
        self.suffix = set()
        self.ip = defaultdict(set)
        self.other = set()

    def covers(self, key):
        kind, value, flags = key
        if kind == "DOMAIN":
            return (value, flags) in self.exact or any(
                (parent, flags) in self.suffix for parent in ancestors(value))
        if kind == "DOMAIN-SUFFIX":
            return any((parent, flags) in self.suffix for parent in ancestors(value))
        if kind in IP_KINDS:
            network = ipaddress.ip_network(value, strict=False)
            available = self.ip[(kind, flags)]
            while True:
                if network in available:
                    return True
                if not network.prefixlen:
                    break
                network = network.supernet()
        return key in self.other

    def add(self, key):
        kind, value, flags = key
        if kind == "DOMAIN":
            self.exact.add((value, flags))
        elif kind == "DOMAIN-SUFFIX":
            self.suffix.add((value, flags))
        elif kind in IP_KINDS:
            self.ip[(kind, flags)].add(ipaddress.ip_network(value, strict=False))
        else:
            self.other.add(key)


def prune_against_prior(raw: bytes, prior: PriorPolicyIndex) -> tuple[bytes, list[dict]]:
    """Drop a later predicate only when a strictly earlier same-policy rule covers it."""
    lines = raw.decode("utf-8").splitlines(keepends=True)
    omitted = set()
    removed = []
    current_keys = []
    for index, line in enumerate(lines):
        rule = line.strip()
        if not rule or rule.startswith(("#", ";", "//")):
            continue
        key = rule_fields(rule)
        if prior.covers(key):
            omitted.add(index)
            removed.append({"line": index + 1, "rule": rule,
                            "reason": "EARLIER_SAME_POLICY_DOMINANCE"})
        else:
            current_keys.append(key)
    # Do not include the current subscription until all of its rules are
    # considered; otherwise same-subscription ordering could be misread.
    for key in current_keys:
        prior.add(key)
    return "".join(line for i, line in enumerate(lines) if i not in omitted).encode("utf-8"), removed


def safe_candidate_output(root: Path, directory: str, filename: str) -> Path:
    relative = Path(directory)
    if (relative.is_absolute() or ".." in relative.parts or
            relative.parts[:2] != ("build", "rule_candidates") or len(relative.parts) < 3):
        raise ValueError("optimization output must live under build/rule_candidates/<version>")
    target = root / relative / filename
    current = target
    while current != root and current.is_relative_to(root):
        if current.is_symlink():
            raise ValueError("candidate output must not follow symlinks")
        current = current.parent
    if not target.resolve().is_relative_to((root / "build" / "rule_candidates").resolve()):
        raise ValueError("candidate output escaped its private directory")
    return target


def audit(root: Path = ROOT, *, write_dir: str | None = None) -> dict:
    manifest = json.loads((root / "build/release_manifest.json").read_text(encoding="utf-8"))
    records = manifest["runtime_resources"]
    result = {}
    samples = {}
    counts = Counter()
    totals = Counter()
    by_kind = Counter()
    by_kind_policy = defaultdict(Counter)
    first_owner = {}
    cross_policy_conflicts = Counter()
    conflict_examples = []
    potential_dns_ip_lookups = Counter()
    policy_indexes = defaultdict(PriorPolicyIndex)
    for row in records:
        path = root / row["path"]
        source = path.read_bytes()
        if hashlib.sha256(source).hexdigest() != row["sha256"]:
            raise ValueError("unverified input bytes: " + row["path"])
        for record in source.decode("utf-8").splitlines():
            line = record.strip()
            if not line or line.startswith(("#", ";", "//")):
                continue
            kind, value, flags = rule_fields(line)
            by_kind[kind] += 1
            by_kind_policy[row["policy"]][kind] += 1
            if kind in IP_KINDS and "no-resolve" not in flags:
                potential_dns_ip_lookups[row["tag"]] += 1
            key = (kind, value, flags)
            known = first_owner.get(key)
            if known is None:
                first_owner[key] = (row["tag"], row["policy"])
            elif known[1] != row["policy"]:
                cross_policy_conflicts[(known[1], row["policy"])] += 1
                if len(conflict_examples) < 20:
                    conflict_examples.append({"rule": line, "earlier": known[0],
                                              "earlier_policy": known[1], "later": row["tag"],
                                              "later_policy": row["policy"]})
        dest, summary, removed = trim_rules(source)
        if summary["before"] != row["matcher_count"]:
            raise ValueError("manifest count mismatch: " + row["path"])
        earlier, more_removed = prune_against_prior(dest, policy_indexes[row["policy"]])
        dest = earlier
        summary["locally_removed"] = summary["removed"]
        summary["globally_removed"] = len(more_removed)
        summary["removed"] += len(more_removed)
        summary["after"] -= len(more_removed)
        summary["bytes_after"] = len(dest)
        summary["optimized_sha256"] = hashlib.sha256(dest).hexdigest()
        summary["reasons"] = dict(Counter(summary["reasons"]) +
                                  Counter(r["reason"] for r in more_removed))
        removed += more_removed
        if summary["removed"] and write_dir:
            target = safe_candidate_output(root, write_dir, path.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_file() and target.read_bytes() != dest:
                raise ValueError("existing candidate output differs; choose a new version directory")
            target.write_bytes(dest)
        elif write_dir:
            target = safe_candidate_output(root, write_dir, path.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_file() and target.read_bytes() != source:
                raise ValueError("existing candidate output differs; choose a new version directory")
            target.write_bytes(source)
        result[row["tag"]] = {"source": row["path"], "policy": row["policy"], **summary}
        samples[row["tag"]] = removed[:3]
        counts.update(summary["reasons"])
        totals.update({"before": summary["before"], "after": summary["after"],
                       "removed": summary["removed"], "bytes_before": summary["bytes_before"],
                       "bytes_after": summary["bytes_after"]})
    report = {"algorithm": "same_and_earlier_same_policy_equivalent_subsumption_v2",
              "version": manifest["label"], "sources": len(records),
              "totals": dict(totals), "reasons": dict(counts),
              "resources": result, "examples": samples,
              "rule_kinds": dict(sorted(by_kind.items())),
              "expensive_rule_count": sum(by_kind.get(k, 0)
                                            for k in ("DOMAIN-KEYWORD", "USER-AGENT", "URL-REGEX")),
              "dns_resolving_ip_rules": dict(potential_dns_ip_lookups),
              "cross_policy_exact_collision_count": sum(cross_policy_conflicts.values()),
              "cross_policy_examples": conflict_examples,
              "cross_policy_pairs": {a + " => " + b: n
                                     for (a, b), n in sorted(cross_policy_conflicts.items())},
              "expensive_by_policy": {
                  owner: {kind: n for kind, n in sorted(kinds.items())
                          if kind in ("DOMAIN-KEYWORD", "USER-AGENT", "URL-REGEX")}
                  for owner, kinds in sorted(by_kind_policy.items())
                  if any(kinds.get(kind, 0) for kind in ("DOMAIN-KEYWORD", "USER-AGENT", "URL-REGEX"))
              }}
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
                      "reasons": report["reasons"], "rule_kinds": report["rule_kinds"],
                      "expensive_rule_count": report["expensive_rule_count"],
                      "dns_resolving_ip_rules": report["dns_resolving_ip_rules"],
                      "cross_policy_exact_collision_count": report["cross_policy_exact_collision_count"],
                      "cross_policy_examples": report["cross_policy_examples"],
                      "cross_policy_pairs": report["cross_policy_pairs"],
                      "top": sorted(((k, v["removed"], v["bytes_before"] - v["bytes_after"])
                                     for k, v in report["resources"].items()),
                                    key=lambda x: x[1], reverse=True)[:15]},
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
