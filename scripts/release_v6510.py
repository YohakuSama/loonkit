"""Verify v6.5.10 as an exact, minimal node-latency URL patch of frozen v6.5.9.

Only the General proxy-test-url and the Auto/Fallback URL fields change.
In particular internet-test-url, DNS, rules, plugins, scripts and the internal
beta profile remain unchanged. This does not prove physical egress latency.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from release_v659 import render as render_v659
from reviewed_release import sha, validate_records
from beta_channel import ROOT, content_rules

OLD = "http://cp.cloudflare.com/generate_204"
NEW = "http://www.bing.com"
PREVIOUS = "c0e2bbc6f4565104a7bfa4474d2ac63df617dcc1805216b942712d361d1c23b1"
VERSION = "v6.5.10"


def render(root=ROOT):
    archived = (root / "build/baselines/v6.5.9/LoonKit.lcf").read_bytes()
    if sha(archived) != PREVIOUS or archived != render_v659(root):
        raise ValueError("v6.5.9 archived release drifted")
    profile = archived.decode("utf-8")
    if not profile.startswith("# LoonKit v6.5.9\n"):
        raise ValueError("unexpected v6.5.9 header")
    if profile.count(OLD) != 3:
        raise ValueError("expected exactly 3 Cloudflare node speed probes")
    updated = profile.replace("# LoonKit v6.5.9\n", "# LoonKit v6.5.10\n", 1)
    updated = updated.replace(OLD, NEW)
    if updated.count(NEW) != 3:
        raise ValueError("not exactly three Bing speed probes")
    if "internet-test-url = http://wifi.vivo.com.cn/generate_204" not in updated:
        raise ValueError("direct internet-check URL must be preserved")
    return updated.encode("utf-8")


def verify(root=ROOT, remote=False):
    from verify_release import check_public_checksums, check_lock
    spec = json.loads((root / "build/release_spec.json").read_text())
    meta = json.loads((root / "build/release_manifest.json").read_text())
    prev_spec = json.loads((root / "build/baselines/v6.5.9/release_spec.json").read_text())
    prev_meta = json.loads((root / "build/baselines/v6.5.9/release_manifest.json").read_text())
    archived = (root / "build/baselines/v6.5.9/LoonKit.lcf").read_bytes()
    profile = (root / "LoonKit.lcf").read_bytes()
    if (spec["stable_release_version"], meta["label"]) != (VERSION, VERSION):
        raise ValueError("v6.5.10 version mismatch")
    if (prev_spec["stable_release_version"], prev_meta["label"]) != ("v6.5.9", "v6.5.9"):
        raise ValueError("v6.5.9 archive identity mismatch")
    if prev_meta["profile_sha256"] != {"LoonKit.lcf": sha(archived)}:
        raise ValueError("historical manifest checksum mismatch")
    if spec["previous_formal_profile_sha256"] != PREVIOUS or spec["historical_profile_sha256"]["v6.5.9"] != PREVIOUS:
        raise ValueError("historical checksum omitted")
    if spec["previous_formal_profile_path"] != "build/baselines/v6.5.9/LoonKit.lcf":
        raise ValueError("wrong previous profile path")
    if profile != render(root):
        raise ValueError("only version and three speed URLs can change")
    digest = sha(profile)
    decision = json.loads((root / spec["release_gate_file"]).read_text())
    if (decision["version"] != VERSION or decision["release_profile_sha256"] != digest
            or decision["decision"] != "OWNER_REQUESTED_BING_LATENCY_PROBE_CANDIDATE"):
        raise ValueError("unapproved release candidate")
    if meta["runtime_resources"] != prev_meta["runtime_resources"]:
        raise ValueError("rules and order changed in speed-only release")
    if (meta["remote_subscription_count"], meta["remote_rule_count"]) != (36, 196486):
        raise ValueError("remote rule totals changed")
    if meta["plugin_sha256"] != prev_meta["plugin_sha256"] or meta["plugin_path"] != prev_meta["plugin_path"]:
        raise ValueError("plugin changed")
    for path in ("beta/LoonKit.lcf",):
        if not (root / path).is_file():
            raise ValueError("internal beta disappeared")
    if "GEOIP,CN,DIRECT,no-resolve" not in profile.decode():
        raise ValueError("native geoip fallback changed")
    for service in ("AppleOTA", "Bilibili", "Microsoft", "Apple", "Paypal"):
        lines = content_rules((root / f"rules/releases/v6.5.9/{service}.list").read_bytes())
        if not lines or any(x.startswith(("AND,", "OR,", "NOT,")) for x in lines):
            raise ValueError("v6.5.9 service composite reintroduced")
    check_public_checksums(root, meta, spec)
    check_lock(root)
    resources = validate_records(profile, meta["runtime_resources"], root, remote=remote)
    if len(resources) != 36 or sum(r["matcher_count"] for r in resources) != 196486:
        raise ValueError("resource validation mismatch")
    return {"release": VERSION, "resources": 36, "matchers": 196486,
            "sha256": digest, "remote_checked": remote,
            "device_test": "NOT_TESTED"}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", required=True)
    p.add_argument("--remote", action="store_true")
    args = p.parse_args()
    print(json.dumps(verify(remote=args.remote), sort_keys=True))
