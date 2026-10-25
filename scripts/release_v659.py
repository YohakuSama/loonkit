"""Reproducible v6.5.9 native-only routing release and frozen v6.5.8 checks.

Never rewrite the published v6.5.8 release. The v6.5.9 profile is an exact
patch over that frozen profile: five rule URLs become ordinary domain matchers,
and the redundant remote RegionalCN entry is removed. The existing local
GEOIP,CN,DIRECT,no-resolve and FINAL,Final directives remain unchanged.

This audit does not claim DNS-leak elimination or restoration of per-domain
CN/non-CN dynamic destination routing (which ordinary domain rules cannot do).
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from beta_channel import ROOT, content_rules, remote_entries, section
from reviewed_release import validate_records, sha

RELEASE = "v6.5.9"
PREVIOUS = "v6.5.8"
PINNED_RULE_COMMIT = "8452034ad371e75d13fd3ff2a17eff92f1149727"
OLD_RULE_COMMIT = "7f11406a1b958cbf4f64d3281ead6ce417a19dbf"
SERVICES = ("AppleOTA", "Bilibili", "Microsoft", "Apple", "Paypal")
EXPECTED_COUNTS = {
    "AppleOTA": 82, "Bilibili": 120, "Microsoft": 645,
    "Apple": 1561, "Paypal": 246,
}
OLD_REGIONAL_COUNT = 2553
OLD_TOTAL = 199060
NEW_TOTAL = 196486
NEW_RESOURCE_COUNT = 36
SOURCE = ROOT / "build/baselines/v6.5.8/LoonKit.lcf"
COMPOSITE = re.compile(
    r"AND,\(\(((?:DOMAIN|DOMAIN-SUFFIX|IP-CIDR|IP-CIDR6|IP-ASN),[^()]+)\),"
    r"\((GEOIP,CN|NOT,\(\(GEOIP,CN\)\))\)\)\Z"
)
DOMAIN = re.compile(r"DOMAIN(?:-SUFFIX)?,[^(),\s]+\Z")
RAW = "https://raw.githubusercontent.com/YohakuSama/loonkit/"


def render(root=ROOT):
    original = (root / "build/baselines/v6.5.8/LoonKit.lcf").read_text(encoding="utf-8")
    result, seen, regional_removed = [], set(), 0
    for index, line in enumerate(original.splitlines()):
        if index == 0:
            if line != "# LoonKit v6.5.8":
                raise ValueError("unexpected archived v6.5.8 profile header")
            result.append("# LoonKit v6.5.9")
            continue
        if "tag=Our-RegionalCN," in line:
            if not line.startswith(RAW + OLD_RULE_COMMIT + "/rules/releases/v6.5.8/RegionalCN.list"):
                raise ValueError("unrecognized archived RegionalCN rule reference")
            regional_removed += 1
            continue
        match = re.search(r"(?:^|,)\s*tag=Our-([^,]+)", line)
        if match and match[1] in SERVICES:
            name = match[1]
            old = RAW + OLD_RULE_COMMIT + f"/rules/releases/v6.5.8/{name}.list"
            new = RAW + PINNED_RULE_COMMIT + f"/rules/releases/v6.5.9/{name}.list"
            if not line.startswith(old + ","):
                raise ValueError("unrecognized archived service rule URL " + name)
            line = line.replace(old, new, 1)
            seen.add(name)
        result.append(line)
    if seen != set(SERVICES) or regional_removed != 1:
        raise ValueError("expected precisely five replacements and one redundant removal")
    return ("\n".join(result) + "\n").encode()


def rebuilt_service(name, root=ROOT):
    if name not in SERVICES:
        raise ValueError("unknown native service")
    raw = content_rules((root / f"rules/releases/v6.5.8/{name}.list").read_bytes())
    fields = []
    for expression in raw:
        m = COMPOSITE.fullmatch(expression)
        if not m or m.group(2) != "NOT,((GEOIP,CN))":
            raise ValueError("unexpected original composite Loon rule: " + expression[:120])
        child = m.group(1)
        if DOMAIN.fullmatch(child):
            fields.append(child)
        elif not child.startswith(("IP-CIDR,", "IP-CIDR6,", "IP-ASN,")):
            raise ValueError("unknown matcher kind: " + child)
    if len(fields) != EXPECTED_COUNTS[name] or len(fields) != len(set(fields)):
        raise ValueError("reviewed domain-only matcher inventory changed: " + name)
    return (
        "# LoonKit v6.5.9 " + name + " Loon-native domain rules\n"
        "# Source: v6.5.8 reviewed rules, composite GeoIP conditions removed.\n"
        "# CN/overseas GeoIP dual-routing cannot be preserved using domain-only matchers.\n"
        + "\n".join(fields) + "\n"
    ).encode()


def verify(root=ROOT, remote=False):
    from release_v658 import verify as verify_previous
    from verify_release import check_public_checksums, check_lock
    previous = verify_previous(root, remote=remote)
    spec = json.loads((root / "build/release_spec.json").read_text())
    meta = json.loads((root / "build/release_manifest.json").read_text())
    original = (root / "build/baselines/v6.5.8/LoonKit.lcf").read_bytes()
    profile = (root / "LoonKit.lcf").read_bytes()
    decision = json.loads((root / spec["release_gate_file"]).read_text())

    if (spec["stable_release_version"], meta["label"]) != (RELEASE, RELEASE):
        raise ValueError("formal v6.5.9 version mismatch")
    if spec["previous_formal_profile_sha256"] != sha(original):
        raise ValueError("v6.5.8 archived profile differs")
    if spec["previous_formal_profile_path"] != "build/baselines/v6.5.8/LoonKit.lcf":
        raise ValueError("v6.5.8 rollback path unrecognized")
    if spec["native_rules_release_commit"] != PINNED_RULE_COMMIT:
        raise ValueError("active rule commit did not match audited candidate")
    if profile != render(root):
        raise ValueError("v6.5.9 profile is not exact approved patch from archived release")
    if (decision["version"] != RELEASE
            or decision["decision"] != "USER_REQUESTED_REMOVE_GEOIP_COMPOSITES_AND_PUBLISH"
            or decision["release_profile_sha256"] != sha(profile)):
        raise ValueError("owner decision does not cover the exact release")
    check_public_checksums(root, meta, spec)
    check_lock(root)

    for name in SERVICES:
        path = root / f"rules/releases/v6.5.9/{name}.list"
        if path.read_bytes() != rebuilt_service(name, root):
            raise ValueError("native-only service matcher differs from source: " + name)
        lines = content_rules(path.read_bytes())
        if any(x.startswith(("AND,", "OR,", "NOT,", "GEOIP,")) for x in lines):
            raise ValueError("logical GEOIP rule survived conversion " + name)

    records = validate_records(profile, meta["runtime_resources"], root, remote=remote)
    if len(records) != NEW_RESOURCE_COUNT or any(r["tag"] == "Our-RegionalCN" for r in records):
        raise ValueError("redundant regional CN remote subscription still enabled")
    if len(records) != meta["runtime_rule_count"] or len(records) != meta["remote_subscription_count"]:
        raise ValueError("remote subscription count mismatch")
    if sum(row["matcher_count"] for row in records) != NEW_TOTAL:
        raise ValueError("unexpected total matchers in v6.5.9")
    if meta["runtime_rule_matcher_count"] != NEW_TOTAL or meta["remote_rule_count"] != NEW_TOTAL:
        raise ValueError("manifest matcher count mismatch")
    known = {row["tag"]: row for row in records}
    for name in SERVICES:
        row = known["Our-" + name]
        if (row["path"] != f"rules/releases/v6.5.9/{name}.list"
            or row["commit"] != PINNED_RULE_COMMIT
            or row["matcher_count"] != EXPECTED_COUNTS[name]):
            raise ValueError("native service wrong pin, path or count: " + name)

    original_text, live_text = original.decode("utf-8"), profile.decode("utf-8")
    for name in ("General", "Proxy", "Remote Proxy", "Remote Filter",
                 "Proxy Group", "Host", "Rule", "Plugin"):
        if section(original_text, name) != section(live_text, name):
            raise ValueError("protected DNS, proxy, rule or plugin section changed: " + name)
    if content_rules(("\n".join(section(live_text, "Rule").splitlines())).encode())[-2:] != [
            "GEOIP,CN,DIRECT,no-resolve", "FINAL,Final"]:
        raise ValueError("fixed last two rules were modified")
    manifest_previous = json.loads((root / "build/baselines/v6.5.8/release_manifest.json").read_text())
    original_tags = [r["tag"] for r in manifest_previous["runtime_resources"]]
    allowed_tags = [t for t in original_tags if t != "Our-RegionalCN"]
    if list(known) != allowed_tags:
        raise ValueError("resource ordering/identities changed unexpectedly")
    if meta["rules"] != manifest_previous["rules"] or meta["source_group_tags"] != manifest_previous["source_group_tags"]:
        raise ValueError("unrelated source registry changed")
    for group, count in meta["source_group_counts"].items():
        original_count = manifest_previous["source_group_counts"][group]
        expected = EXPECTED_COUNTS.get(group, original_count)
        if count != expected:
            raise ValueError("unreviewed group size: " + group)
    if "**v6.5.9**" not in (root / "README.md").read_text():
        raise ValueError("README not updated for v6.5.9")

    return {
        "release": RELEASE,
        "resources": len(records),
        "matchers": NEW_TOTAL,
        "sha256": sha(profile),
        "previous_release": previous["release"],
        "remote_checked": remote,
        "warnings": ["DNS leaks not resolved", "same-domain CN/overseas routing not equivalent"],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--check", required=True, action="store_true")
    p.add_argument("--remote", action="store_true")
    args = p.parse_args()
    print(json.dumps(verify(remote=args.remote), sort_keys=True))
