"""Verify the v7.0.4 routing-only formal release against the frozen v7.0.3 base."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "v7.0.4"
PREVIOUS = "v7.0.3"
PREVIOUS_SHA = "bf68380929f713989251e68a8f82f9a256486e89aae31882405f000bb1ce3616"
PIN = "d82214d057b27a68d6b9c07c61fb126a69adc903"
LOCAL_TRAE = (
    "DOMAIN,trae-api-sg.mchost.guru,AI",
    "DOMAIN,trae-api-us.mchost.guru,AI",
)
DIRECT_GROUPS = ("Apple", "Microsoft", "Bilibili", "Speedtest", "Line")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def section(text: str, name: str) -> str:
    start = text.index("[" + name + "]\n") + len(name) + 3
    end = text.find("\n[", start)
    return text[start:end if end >= 0 else None]


def render(previous: bytes) -> bytes:
    text = previous.decode("utf-8")
    if not text.startswith("# LoonKit v7.0.3\n"):
        raise ValueError("not the immutable previous release")
    text = text.replace("# LoonKit v7.0.3\n", "# LoonKit v7.0.4\n", 1)
    old = "AdBlock = select,REJECT,Proxy,"
    if text.count(old) != 1:
        raise ValueError("AdBlock baseline changed")
    text = text.replace(old, "AdBlock = select,REJECT,DIRECT,Proxy,", 1)
    for group in DIRECT_GROUPS:
        old = group + " = select,Proxy,Auto,Fallback,ALL_Filter,"
        if text.count(old) != 1:
            raise ValueError("missing previous service policy: " + group)
        text = text.replace(old, group + " = select,DIRECT,Proxy,Auto,Fallback,ALL_Filter,", 1)
    before = "DOMAIN-SUFFIX,raw.githubusercontent.com,Proxy\n"
    if text.count(before) != 1:
        raise ValueError("local rule insertion point changed")
    text = text.replace(before, before + "".join(rule + "\n" for rule in LOCAL_TRAE), 1)
    return text.encode("utf-8")


def check(remote: bool = False, root: Path = ROOT) -> dict:
    from reviewed_release import validate_records
    from verify_release import check_public_checksums
    from audit_upstream_703 import owner
    from audit_v702 import lines

    spec = json.loads((root / "build/release_spec.json").read_text())
    manifest = json.loads((root / "build/release_manifest.json").read_text())
    previous = (root / "build/candidates/v7.0.3/LoonKit.lcf").read_bytes()
    candidate = json.loads((root / "build/candidates/v7.0.3/candidate_manifest.json").read_text())
    current = (root / "LoonKit.lcf").read_bytes()
    previous_text, current_text = previous.decode(), current.decode()
    actual = sha(current)
    if (spec["stable_release_version"] != VERSION or manifest["label"] != VERSION
            or spec["historical_profile_sha256"].get(PREVIOUS) != PREVIOUS_SHA
            or spec.get("previous_formal_profile_sha256") != PREVIOUS_SHA
            or spec.get("release_assets_commit") != PIN
            or sha(previous) != PREVIOUS_SHA):
        raise ValueError("v7.0.4 or archived v7.0.3 identity changed")
    if current != render(previous):
        raise ValueError("unreviewed change to immutable routing baseline")
    if manifest["profile_sha256"] != {"LoonKit.lcf": actual}:
        raise ValueError("published v7.0.4 profile digest mismatch")
    if (len(manifest["runtime_resources"]) != 43
            or manifest["runtime_resources"] != candidate["rule_sets"]
            or manifest["remote_subscription_count"] != 43
            or spec.get("release_rules_dir") != "rules/releases/v7.0.3"):
        raise ValueError("frozen remote subscriptions, owners or checksums changed")
    rules = section(current_text, "Rule")
    if not all(rule in rules.splitlines() for rule in LOCAL_TRAE):
        raise ValueError("TRAE AI route missing")
    for group in DIRECT_GROUPS:
        if not re.search(r"(?m)^" + group + r" = select,DIRECT,Proxy,Auto,Fallback,ALL_Filter,", section(current_text, "Proxy Group")):
            raise ValueError("missing service direct option: " + group)
    if "AdBlock = select,REJECT,DIRECT,Proxy," not in section(current_text, "Proxy Group"):
        raise ValueError("ad-block bypass missing")
    for protected in ("General", "Proxy", "Remote Proxy", "Remote Filter", "Remote Rule", "Host", "Plugin"):
        if section(previous_text, protected) != section(current_text, protected):
            raise ValueError("protected runtime section changed: " + protected)
    local = [line.strip() for line in rules.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not (local[-2:] == ["GEOIP,CN,DIRECT,no-resolve", "FINAL,Final"]):
        raise ValueError("local fallthrough changed")
    records = validate_records(current, manifest["runtime_resources"], root, remote=remote)
    if (sum(row["matcher_count"] for row in records) != manifest["remote_rule_count"]
            or manifest["remote_rule_count"] != manifest["runtime_rule_matcher_count"]):
        raise ValueError("rule matcher inventory differs")
    remote_rules = {row["path"]: lines((root / row["path"]).read_bytes()) for row in records}
    expected = {
        "trae-api-sg.mchost.guru": "AI",
        "trae-api-us.mchost.guru": "AI",
        "trae.ai": "AI",
        "www.bilibili.com": "Bilibili",
        "mesu.apple.com": "Apple",
        "www.speedtest.net": "Speedtest",
        "raw.githubusercontent.com": "Proxy",
        "github.com": "GitHub",
        "gemini.google.com": "Gemini",
        "speed.cloudflare.com": "Speedtest",
    }
    for host, policy in expected.items():
        if owner(host, remote_rules, records, local) != policy:
            raise ValueError("unexpected policy owner for " + host)
    gate = json.loads((root / spec["release_gate_file"]).read_text())
    if (gate.get("decision") != "OWNER_REQUESTED_FORMAL_PUBLICATION"
            or gate.get("version") != VERSION or gate.get("release_profile_sha256") != actual
            or gate.get("real_device_test") != "NOT_ATTESTED"):
        raise ValueError("formal release decision or device status inconsistent")
    check_public_checksums(root, manifest, spec)
    return {
        "version": VERSION,
        "profile_sha256": actual,
        "strategy_groups": 39,
        "remote_subscriptions": len(records),
        "remote_matchers": manifest["remote_rule_count"],
        "remote_checked": remote,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", required=True)
    p.add_argument("--remote", action="store_true")
    args = p.parse_args()
    print(json.dumps(check(remote=args.remote), sort_keys=True))
