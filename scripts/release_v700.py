"""Deterministic v7.0.0 formal release over the immutable v6.5.10 profile.

The runtime selectors, rules, DNS, TUN, plugins, and node probes are unchanged.
Only the version header and visible subscription tag prefixes are modified.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from beta_channel import ROOT, remote_entries, content_rules, section
from release_v6510 import render as render_v6510
from reviewed_release import sha, validate_records

VERSION = "v7.0.0"
PREVIOUS = "v6.5.10"
PREVIOUS_SHA = "dad4a801d387ef9d41e0db53b62b74de2848da24520dd08f90b15a824c83f111"

def render(root=ROOT):
    old = (root / "build/baselines/v6.5.10/LoonKit.lcf").read_bytes()
    if sha(old) != PREVIOUS_SHA or old != render_v6510(root):
        raise ValueError("immutable v6.5.10 release changed")
    source = old.decode("utf-8")
    if not source.startswith("# LoonKit v6.5.10\n"):
        raise ValueError("unexpected former release header")
    result = source.replace("# LoonKit v6.5.10\n", "# LoonKit v7.0.0\n", 1)
    result = re.sub(r"(?<=tag=)Beta-", "Our-", result)
    if "tag=Beta-" in result:
        raise ValueError("legacy beta subscription labels remain")
    old_rows = remote_entries(source)
    new_rows = remote_entries(result)
    if len(old_rows) != 36 or len(new_rows) != 36:
        raise ValueError("remote inventory changed")
    for before, after in zip(old_rows, new_rows):
        for key in ("uri", "commit", "path", "policy", "enabled"):
            if before[key] != after[key]:
                raise ValueError("runtime remote resource changed: " + key)
    for section_name in ("General", "Proxy", "Remote Proxy", "Remote Filter",
                         "Proxy Group", "Host", "Rule", "Plugin"):
        if section(source, section_name) != section(result, section_name):
            raise ValueError("runtime directive changed: " + section_name)
    return result.encode("utf-8")

def verify(root=ROOT, remote=False):
    from verify_release import check_public_checksums, check_lock
    spec = json.loads((root / "build/release_spec.json").read_text())
    meta = json.loads((root / "build/release_manifest.json").read_text())
    decision = json.loads((root / "docs/RELEASE_OWNER_DECISION_v7.0.0.json").read_text())
    old_meta = json.loads((root / "build/baselines/v6.5.10/release_manifest.json").read_text())
    old_spec = json.loads((root / "build/baselines/v6.5.10/release_spec.json").read_text())
    old = (root / "build/baselines/v6.5.10/LoonKit.lcf").read_bytes()
    current = (root / "LoonKit.lcf").read_bytes()
    digest = sha(current)
    if spec["stable_release_version"] != VERSION or meta["label"] != VERSION:
        raise ValueError("formal release version mismatch")
    if old_spec["stable_release_version"] != PREVIOUS or old_meta["label"] != PREVIOUS:
        raise ValueError("former release baseline metadata changed")
    if old_meta["profile_sha256"] != {"LoonKit.lcf": PREVIOUS_SHA} or sha(old) != PREVIOUS_SHA:
        raise ValueError("former release baseline checksum mismatch")
    if (spec["previous_formal_profile_sha256"] != PREVIOUS_SHA or
            spec["previous_formal_profile_path"] != "build/baselines/v6.5.10/LoonKit.lcf" or
            spec["historical_profile_sha256"]["v6.5.10"] != PREVIOUS_SHA):
        raise ValueError("rollback history mismatch")
    if current != render(root):
        raise ValueError("formal profile differs from exact reviewed promotion")
    if (decision["version"] != VERSION or
            decision["decision"] != "OWNER_REQUESTED_V7_FORMAL_PUBLICATION" or
            decision["release_profile_sha256"] != digest):
        raise ValueError("release ownership or checksum mismatch")
    if len(meta["runtime_resources"]) != 36 or meta["remote_rule_count"] != 196486:
        raise ValueError("runtime resources or matcher totals changed")
    if meta["plugin_sha256"] != old_meta["plugin_sha256"]:
        raise ValueError("plugin drifted during release")
    checked = validate_records(current, meta["runtime_resources"], root, remote=remote)
    expected_tags = {r["tag"].replace("Beta-", "Our-", 1) for r in old_meta["runtime_resources"]}
    if {r["tag"] for r in checked} != expected_tags:
        raise ValueError("resource tags inconsistent with archived profile")
    if sum(r["matcher_count"] for r in checked) != 196486:
        raise ValueError("matcher inventory drifted")
    for row in checked:
        rules = content_rules((root / row["path"]).read_bytes())
        if any(x.startswith(("AND,", "OR,", "NOT,")) for x in rules):
            raise ValueError("composite rules prohibited in v7.0.0: " + row["tag"])
    check_public_checksums(root, meta, spec)
    check_lock(root)
    return {"release": VERSION, "resources": len(checked), "matchers": 196486,
            "sha256": digest, "remote_checked": remote}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.add_argument("--remote", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(remote=args.remote), sort_keys=True))
