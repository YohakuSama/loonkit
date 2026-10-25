#!/usr/bin/env python3
"""Validate every active beta resource, not just the historical overlay count."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import urllib.request

from loon_resources import ROOT, URI, section, remote_entries, content_rules

def resource_records(meta: dict) -> dict[str, dict]:
    if meta.get('schema_version') == 2:
        rows = meta['runtime_resources']
        if len({r['uri'] for r in rows}) != len(rows):
            raise ValueError('duplicate channel resource URI')
        return {r['uri']: r for r in rows}
    records = list(meta["overlay_rules"].values()) + [meta["china_direct"], meta["adblock"]]
    records += list(meta.get("upstream_overlays", {}).values())
    result = {}
    for row in records:
        if row["uri"] in result:
            raise ValueError("duplicate manifest resource URI")
        result[row["uri"]] = row
    return result


def validate(root: Path = ROOT, *, remote: bool = False, profile_path="beta/LoonKit.lcf", manifest_path="build/beta_manifest.json") -> dict:
    meta = json.loads((root / manifest_path).read_text())
    profile = (root / profile_path).read_bytes()
    if meta.get("configuration_entry") != "beta/LoonKit.lcf":
        raise ValueError("beta entry must be isolated from production")
    if hashlib.sha256(profile).hexdigest() != meta["configuration_sha256"]:
        raise ValueError("beta profile checksum mismatch")
    if hashlib.sha256((root / "build/baselines/v6.5.4/LoonKit.lcf").read_bytes()).hexdigest() != meta["original_production_config_sha256"]:
        raise ValueError("formal configuration changed during beta work")
    text = profile.decode()
    if text.splitlines()[0] != "# LoonKit " + meta["version"] + " · BETA TEST ONLY":
        raise ValueError("beta version and manifest differ")
    if meta.get('schema_version') == 2:
        from reviewed_release import render_beta, validate_records
        rendered, rebuilt = render_beta(meta, root)
        if rendered != profile or rebuilt != meta:
            raise ValueError('beta profile/manifest is not a reproducible foundation plus routine overlays')
        validate_records(profile, meta['runtime_resources'], root, remote)
        return {'version':meta['version'], 'resources':len(meta['runtime_resources']),
                'remote_verified':remote, 'configuration_sha256':meta['configuration_sha256']}
    records = resource_records(meta)
    published = json.loads((root / "build/baselines/v6.5.4/release_manifest.json").read_text())["rules"]
    formal = {row["path"]: row for row in published.values()}
    entries = remote_entries(text)
    used = set()
    checks = []
    formal_count = 0
    for entry in entries:
        raw = (root / entry["path"]).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if entry["uri"] in records:
            used.add(entry["uri"])
            expected = records[entry["uri"]]
            if sha != expected["sha256"] or len(content_rules(raw)) != expected["matcher_count"]:
                raise ValueError("beta asset hash/count differs: " + entry["path"])
        elif entry["commit"] == meta["production_release_commit"] and entry["path"] in formal:
            formal_count += 1
            if sha != formal[entry["path"]]["sha256"]:
                raise ValueError("historical formal asset changed")
        else:
            raise ValueError("undeclared beta resource: " + entry["uri"])
        checks.append({**entry, "sha256": sha})
    if used != set(records) or formal_count != meta["production_rule_refs_preserved"]:
        raise ValueError("manifest resource set differs from active profile")
    if len(entries) != meta["runtime_remote_count"]:
        raise ValueError("unexpected active beta source count")
    for group, item in meta.get("upstream_overlays", {}).items():
        if not any(r["uri"] == item["uri"] and r["policy"] == group for r in entries):
            raise ValueError("upstream overlay lost its reviewed service owner")
    if remote:
        def verify(row):
            with urllib.request.urlopen(row["uri"], timeout=40) as response:
                if not URI.fullmatch(response.geturl()):
                    raise ValueError("resource redirected outside immutable repository URL")
                data = response.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ValueError("published immutable bytes differ: " + row["path"])
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(verify, checks))
    return {"version": meta["version"], "resources": len(checks), "remote_verified": remote,
            "configuration_sha256": meta["configuration_sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", action="store_true")
    args = parser.parse_args()
    print(json.dumps(validate(remote=args.remote), sort_keys=True))
