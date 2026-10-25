#!/usr/bin/env python3
"""Strict read-only formal release integrity check for the current locked version."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib import request
from rule_engine import compile_rules
from source_lock import check_lock

ROOT = Path(__file__).resolve().parents[1]
RAW = "https://raw.githubusercontent.com/YohakuSama/loonkit/"
LINK = re.compile(r'https://raw[.]githubusercontent[.]com/YohakuSama/loonkit/([a-f0-9]{40})/([^,\s")]+)')
DNS = ("dns-server", "doh-server", "hijack-dns", "ip-mode", "ipv6-vif",
       "interface-mode", "skip-proxy", "bypass-tun", "real-ip")


def sha(content):
    return hashlib.sha256(content).hexdigest()


def section(profile, name):
    start = profile.index("[" + name + "]")
    end = profile.find("\n[", start+1)
    return profile[start:end if end >= 0 else None]



def check_public_checksums(root: Path, release: dict, spec: dict) -> str:
    """Read-only agreement check; never regenerate a release manifest or profile."""
    version = spec["stable_release_version"]
    digest = sha((root / "LoonKit.lcf").read_bytes())
    if release["label"] != version or release["profile_sha256"] != {"LoonKit.lcf": digest}:
        raise ValueError("published profile/manifest checksum or version mismatch")

    # Verify each historical published checksum without rewriting any prior record.
    legacy = {
        "v6.5.2": "e98dc568485ac4be1240a475e6c2beee60feb9ab5ce3afc19e7d96be81f6a5de",
        "v6.5.3": "3ca24609dadd075a31116c75c0358ec252bf301c15c47bc5c1d98b140832c3a1",
    }
    expected = {version: digest}
    if version in ("v6.5.3", "v6.5.4"):
        expected["v6.5.2"] = legacy["v6.5.2"]
    if version in ("v6.5.4", "v6.5.5", "v6.5.6"):
        expected["v6.5.3"] = legacy["v6.5.3"]
    if version in ("v6.5.5", "v6.5.6"):
        expected["v6.5.2"] = legacy["v6.5.2"]
        expected["v6.5.4"] = "6bb6f4dc936e250fbff36763391a976a7f3d7bc833ea549c322832a9c3086a69"
    if version == "v6.5.6":
        expected["v6.5.5"] = "d97984a42e313e5b4fc81c26ce760fd4d1163275ad7278e3930cbce69dcf9f03"
    if spec.get('schema_version') == 2:
        # Explicit versioned history replaces the old growing version ladder.
        for old, value in spec['historical_profile_sha256'].items():
            if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', old) or not re.fullmatch(r'[a-f0-9]{64}', value):
                raise ValueError('invalid historical checksum identity')
            expected[old] = value
    expected_docs = sorted(root / "docs" / ("RELEASE_CHECKSUM_" + v + ".md") for v in expected)
    expected_sums = sorted(root / "release" / ("SHA256SUMS." + v) for v in expected)
    if (sorted((root / "docs").glob("RELEASE_CHECKSUM_*.md")) != expected_docs
            or sorted((root / "release").glob("SHA256SUMS.*")) != expected_sums):
        raise ValueError("unexpected missing, stale or duplicate public checksum files")
    for ver, value in sorted(expected.items()):
        doc_path = root / "docs" / ("RELEASE_CHECKSUM_" + ver + ".md")
        sums_path = root / "release" / ("SHA256SUMS." + ver)
        expected_line = value + "  LoonKit.lcf"
        if sums_path.read_text(encoding="utf-8") != expected_line + "\n":
            raise ValueError("release SHA256SUMS does not match pinned version " + ver)
        document = doc_path.read_text(encoding="utf-8")
        if (ver not in document or
                re.findall(r"(?m)^[0-9a-f]{64}  LoonKit\.lcf$", document) != [expected_line] or
                len(re.findall(r"\b[0-9a-f]{64}\b", document)) != 1):
            raise ValueError("release checksum documentation does not match pinned version " + ver)
    return digest


def verify(remote=False):
    current = json.loads((ROOT/"build/release_spec.json").read_text())
    if current.get('schema_version') == 2:
        if current.get('stable_release_version') == 'v6.5.10':
            from release_v6510 import verify as verify_v6510
            return verify_v6510(remote=remote)
        if current.get('stable_release_version') == 'v6.5.9':
            from release_v659 import verify as verify_v659
            return verify_v659(remote=remote)
        from reviewed_release import verify as verify_reviewed
        return verify_reviewed(remote=remote)
    if current["stable_release_version"] == "v6.5.6":
        from verify_release_v656 import verify as verify_v656
        return verify_v656(remote=remote)
    if current["stable_release_version"] == "v6.5.5":
        from verify_promoted import verify as verify_v655
        return verify_v655(remote=remote)
    spec = json.loads((ROOT/"build/release_spec.json").read_text())
    release = json.loads((ROOT/"build/release_manifest.json").read_text())
    check_public_checksums(ROOT, release, spec)
    checked = check_lock(ROOT)
    compiled = {key.removeprefix("build/generated/"): data.encode("utf-8")
                for key, data in compile_rules(ROOT).items()
                if key.startswith("build/generated/") and key.endswith(".list")}
    if spec["release_rules_dir"] != "rules/releases/vNext-RC2" or spec["source_snapshot_dir"] != "rules/inputs":
        raise ValueError("release input/output directory changed")
    if len(compiled) != len(release["rules"]) or len(compiled) != 26:
        raise ValueError("wrong number of published rule groups")
    total = 0
    for group, info in sorted(release["rules"].items()):
        name = group + ".list"
        if info["path"] != "rules/releases/vNext-RC2/" + name or name not in compiled:
            raise ValueError("rule or manifest path missing: " + group)
        data = (ROOT/info["path"]).read_bytes()
        if data != compiled[name] or sha(data) != info["sha256"]:
            raise ValueError("released rule differs from locked rebuild: " + group)
        count = sum(bool(line) and not line.startswith("#") for line in data.decode().splitlines())
        if count != info["rule_count"]:
            raise ValueError("rule count changed: " + group)
        total += count
    if total != release["remote_rule_count"] or total != 197765:
        raise ValueError("matcher total changed")
    if (ROOT/"LoonKit.PrivacyDNS.lcf").exists():
        raise ValueError("retired alternate profile reintroduced")
    data = (ROOT/"LoonKit.lcf").read_bytes()
    if sha(data) != release["profile_sha256"]["LoonKit.lcf"] or set(release["profile_sha256"]) != {"LoonKit.lcf"}:
        raise ValueError("protected standard profile changed or duplicate profile manifest exists")
    profile = data.decode("utf-8")
    if release["label"] != spec["stable_release_version"]:
        raise ValueError("release label/spec mismatch")
    if not profile.startswith("# LoonKit " + spec["stable_release_version"] + "\n"):
        raise ValueError("unexpected production profile version")
    if (ROOT/"rules/generated").exists() or (ROOT/"rules/ProxyProtect.list").exists() or (ROOT/"rules/active_profile.json").exists():
        raise ValueError("retired compatibility rules reintroduced")
    if (ROOT/"plugins").exists():
        raise ValueError("obsolete plugin aliases reintroduced")
    for profile in (profile,):
        for key in DNS:
            if not re.search(r"(?m)^"+re.escape(key)+r"\s*=",section(profile,"General")):
                raise ValueError("missing DNS/TUN property: " + key)
        if "GEOIP,CN,DIRECT,no-resolve" not in section(profile,"Rule") or "FINAL,Final" not in section(profile,"Rule"):
            raise ValueError("GEOIP or FINAL selector missing")
        if "AdBlock = select,REJECT,DIRECT" not in section(profile,"Proxy Group"):
            raise ValueError("AdBlock selector not selectable")
        links = LINK.findall(profile)
        rules = [(ref,path) for ref,path in links if path.startswith("rules/releases/")]
        icons = [(ref,path) for ref,path in links if path.startswith("icons/")]
        plugins = [(ref,path) for ref,path in links if path=="release/Network_Diagnostics.plugin"]
        if len(rules)!=26 or len(set(path for _,path in rules))!=26 or len(icons)!=33:
            raise ValueError("wrong number of pinned rule/icon subscriptions")
        if any(not path.startswith("icons/v20261021r1/") for _,path in icons) or len({path for _,path in icons})!=33:
            raise ValueError("strategy icons are not consolidated or contain duplicates")

        if plugins != [(spec["plugin_assets_commit"],"release/Network_Diagnostics.plugin")]:
            raise ValueError("network plugin URL unexpectedly changed")
        if spec["stable_release_version"] in ("v6.5.2", "v6.5.3", "v6.5.4"):
            if spec.get("optional_service_plugin_commit") is not None:
                raise ValueError("obsolete secondary plugin still declared")
            if sum(line.startswith(RAW) and line.endswith(".plugin, enabled=true") for line in section(profile, "Plugin").splitlines()) != 1:
                raise ValueError("current version must load exactly one network helper")
            if any(path == "release/Service_Diagnostics.plugin" for _, path in links):
                raise ValueError("second service plugin still active")
        for ref,path in links:
            if not (ROOT/path).is_file():
                raise ValueError("missing referenced asset: " + path)
            if path.startswith("rules/releases/") and (ref!=spec["release_assets_commit"] or path not in [v["path"] for v in release["rules"].values()]):
                raise ValueError("rule pinned ref changed")
            if path.startswith("icons/") and ref != spec["reviewed_auxiliary_commit"]:
                raise ValueError("icon pinned ref changed")
    plugin=(ROOT/release["plugin_path"]).read_bytes()
    if sha(plugin)!=release["plugin_sha256"]:
        raise ValueError("production pinned plugin hash changed")
    # Inspect the embedded immutable URLs as well as the top-level plugin link.
    # The diagnostic path is versioned to avoid stale Loon script caches.
    embedded = LINK.findall(plugin.decode("utf-8"))
    expected_script = "scripts/v20261022r11/network-diagnostics.js"
    node_script = "scripts/v20261022r11/node-intelligence.js"
    service_script = "scripts/v20261022r11/media-unlock.js"
    if spec["stable_release_version"] in ("v6.5.2", "v6.5.3", "v6.5.4"):
        if len(embedded) != 5 or sum(path == expected_script for _,path in embedded) != 2 or sum(path == service_script for _,path in embedded) != 1 or sum(path == node_script for _,path in embedded) != 1:
            raise ValueError("unified plugin must contain icon, node, network x2 and service scripts")
    elif len(embedded) != 4 or sum(path == expected_script for _,path in embedded) != 2:
        raise ValueError("unexpected scripts in network helper")
    for ref,path in embedded:
        expected_ref = (spec["diagnostics_script_commit"] if path == expected_script else
                        spec["node_script_commit"] if path == node_script else
                        spec["unified_service_diagnostics_script_commit"] if path == service_script else
                        spec["script_assets_commit"])
        if ref != expected_ref or not path.startswith(("scripts/", "icons/")):
            raise ValueError("untrusted plugin script/icon reference: " + path)
        if not (ROOT / path).is_file():
            raise ValueError("missing plugin script/icon resource: " + path)
    if spec["stable_release_version"] in ("v6.5.2", "v6.5.3", "v6.5.4"):
        source = plugin.decode("utf-8")
        if source.count("generic then script(") != 3 or source.count("network-changed then script(") != 1:
            raise ValueError("unexpected unified plugin entrypoints")
        if "service = select," in source or "auto_check = switch,false" not in source or 'tag="解锁检测"' not in source:
            raise ValueError("unexpected service selection or missing opt-in reminder")
    if spec["stable_release_version"] in ("v6.5.2", "v6.5.3", "v6.5.4"):
        if (ROOT/"release/Service_Diagnostics.plugin").exists():
            raise ValueError("obsolete standalone service plugin remains")
        for obsolete in ("v20261021r3","v20261021r4","v20261021r5","v20261021r6"):
            if (ROOT/"scripts"/obsolete/"service-diagnostics.js").exists():
                raise ValueError("retired standalone service diagnostic script remains")
    if remote:
        for ref,path in sorted(set(LINK.findall(profile) + embedded)):
            if not path.startswith(("icons/","rules/releases/","release/","scripts/")):
                continue
            with request.urlopen(request.Request(RAW+ref+"/"+path,headers={"User-Agent":"LoonKit-Integrity/1"}),timeout=25) as response:
                live=response.read()
            if sha(live)!=sha((ROOT/path).read_bytes()):
                raise ValueError("Raw content changed: "+path)
    return {"release":spec["stable_release_version"],"rules":26,"matchers":total,"locked_inputs":checked["verified_frozen_inputs"],"profiles":1,"remote_checked":remote}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--check",action="store_true",required=True)
    p.add_argument("--remote",action="store_true")
    a=p.parse_args()
    print(json.dumps(verify(a.remote),sort_keys=True))
