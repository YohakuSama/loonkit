#!/usr/bin/env python3
"""StashKit static compatibility checks against the LoonKit production baseline."""
import hashlib
import ipaddress
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "stashkit"
SOURCE_URL = "https://raw.githubusercontent.com/YohakuSama/loonkit/main/stashkit/rules/"
SUPPORTED = {"DOMAIN", "DOMAIN-SUFFIX", "IP-CIDR", "IP-CIDR6", "IP-ASN"}


class UniqueKeysLoader(yaml.SafeLoader):
    pass


def construct_mapping(loader, node):
    output = {}
    for key, value in node.value:
        k = loader.construct_object(key, deep=True)
        if k in output:
            raise AssertionError(f"Duplicate YAML key: {k}")
        output[k] = loader.construct_object(value, deep=True)
    return output


UniqueKeysLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)


def valid_domain(value):
    assert value and not value.startswith(".") and not value.endswith("."), value
    assert not any(x in value for x in (" ", "/", ",", "*", "+")), value
    # Not a DNS validity oracle; protects against accidentally passing a Clash rule token.
    assert len(value) <= 253, value


def lines_from(path):
    return [row.strip() for row in path.read_text(encoding="utf-8").splitlines()
            if row.strip() and not row.lstrip().startswith("#")]


def generate_source_sets(path):
    buckets = {"domain": [], "ipcidr": [], "asn": []}
    raw = lines_from(path)
    assert len(raw) == len(set(raw)), f"Duplicated LoonKit source entries: {path}"
    for row in raw:
        pieces = row.split(",")
        assert len(pieces) >= 2 and pieces[0] in SUPPORTED, (path, row)
        kind, value = pieces[:2]
        opts = pieces[2:]
        if kind in ("DOMAIN", "DOMAIN-SUFFIX"):
            assert not opts, (path, row)
            valid_domain(value)
            buckets["domain"].append(value if kind == "DOMAIN" else "+." + value)
        elif kind in ("IP-CIDR", "IP-CIDR6"):
            assert opts == ["no-resolve"], (path, row)
            network = ipaddress.ip_network(value, strict=False)
            assert network.version == (4 if kind == "IP-CIDR" else 6), (path, row)
            buckets["ipcidr"].append(value)
        else:
            assert opts == ["no-resolve"] and value.isdigit(), (path, row)
            buckets["asn"].append(row)
    return buckets, len(raw)


def main():
    manifest = json.loads((ROOT / "build/release_manifest.json").read_text(encoding="utf-8"))
    profile = yaml.load((KIT / "StashKit.yaml").read_text(encoding="utf-8"), Loader=UniqueKeysLoader)
    original = (ROOT / "LoonKit.lcf").read_text(encoding="utf-8")
    resources = manifest["runtime_resources"]
    assert manifest["label"] == "v7.0.10", "Regenerate StashKit when LoonKit baseline updates"
    assert len(resources) == manifest["remote_subscription_count"] == 43
    assert profile["mode"] == "rule"
    assert profile["dns"]["nameserver"] == ["https://dns.alidns.com/dns-query"]
    assert "fake-ip-range" in profile["dns"]
    source_groups = original.split("[Proxy Group]", 1)[1].split("[Remote Rule]", 1)[0]
    group_names = [row.split("=", 1)[0].strip() for row in source_groups.splitlines() if " = " in row]
    groups = profile["proxy-groups"]
    names = [group["name"] for group in groups]
    assert len(group_names) == 39 and len(names) == len(set(names)) == 40
    assert names == group_names[:3] + ["ALL"] + group_names[3:], "Group order changed"
    by_name = {group["name"]: group for group in groups}
    assert by_name["Auto"]["type"] == "url-test" and by_name["Auto"]["interval"] == 600
    assert by_name["Auto"]["tolerance"] == 60
    assert by_name["Fallback"]["type"] == "fallback" and by_name["Fallback"]["interval"] == 900
    assert by_name["ALL"]["type"] == "select"
    for group in (by_name["Auto"], by_name["Fallback"], by_name["ALL"]):
        assert group["include-all"] and group["proxies"] == ["REJECT"], "Missing safe empty-node guard"
    assert by_name["AdBlock"]["proxies"][0] == "REJECT"
    assert by_name["Final"]["proxies"][0] == "Proxy"
    assert by_name["Microsoft"]["proxies"][0] == "DIRECT"
    for group in groups:
        for child in group["proxies"]:
            assert child in names or child in ("DIRECT", "REJECT"), (group["name"], child)
        if group.get("icon"):
            assert group["icon"].startswith("https://raw.githubusercontent.com/YohakuSama/loonkit/")
    expected_providers = {}
    expected_routes = []
    total = 0
    domain_count = ip_count = asn_count = 0
    for src in resources:
        original_path = ROOT / src["path"]
        assert original_path.is_file(), src["path"]
        original_bytes = original_path.read_bytes()
        assert hashlib.sha256(original_bytes).hexdigest() == src["sha256"], f"SHA mismatch: {src['path']}"
        buckets, count = generate_source_sets(original_path)
        assert count == src["matcher_count"], f"Source count mismatch: {src['path']}"
        total += count
        base = original_path.stem
        assert src["policy"] == "DIRECT" or src["policy"] in names, src["policy"]
        for behavior in ("domain", "ipcidr", "asn"):
            values = buckets[behavior]
            if not values:
                continue
            path = KIT / "rules" / f"{base}.{behavior}.txt"
            assert path.is_file(), path
            saved = lines_from(path)
            assert saved == values, f"Source parity failed: {path}"
            assert len(saved) == len(set(saved)), f"Generated duplicates: {path}"
            if behavior == "domain":
                for item in saved:
                    valid_domain(item[2:] if item.startswith("+.") else item)
                domain_count += len(saved)
            elif behavior == "ipcidr":
                for item in saved:
                    ipaddress.ip_network(item, strict=False)
                ip_count += len(saved)
            else:
                assert all(re.fullmatch(r"IP-ASN,\d+,no-resolve", item) for item in saved)
                asn_count += len(saved)
            key = f"{base}-{behavior}"
            expected_providers[key] = {
                "behavior": "classical" if behavior == "asn" else behavior,
                "format": "text",
                "url": SOURCE_URL + path.name,
                "interval": 86400,
            }
            expected_routes.append("RULE-SET," + key + "," + src["policy"] + (
                ",no-resolve" if behavior == "ipcidr" else ""))
    assert total == manifest["remote_rule_count"] == 196561, total
    assert profile["rule-providers"] == expected_providers, "Provider names/URL/types are inconsistent"
    assert len(expected_providers) == 54
    assert len(list((KIT / "rules").glob("*.txt"))) == 54
    source_rule_section = original.split("[Rule]", 1)[1].split("[Plugin]", 1)[0]
    source_rules = [row.strip() for row in source_rule_section.splitlines() if row.strip()]
    expected_rules = source_rules[:-2] + expected_routes + ["GEOIP,CN,DIRECT,no-resolve", "MATCH,Final"]
    assert profile["rules"] == expected_rules, "Rules changed order, policy, or local precedence"
    assert profile["rules"][-1] == "MATCH,Final"
    assert len(expected_routes) == 54
    print(f"PASS: {len(resources)} production LoonKit sources; {len(expected_providers)} Stash "
          f"rule providers; {len(names)} groups; {total:,} rules "
          f"({domain_count:,} domain / {ip_count:,} CIDR / {asn_count:,} ASN).")
    print("PASS: SHA-256, no duplicated entries, canonical Stash rule syntax, "
          "no-resolve, provider URLs, all rule paths, routing priority and policy targets.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise
