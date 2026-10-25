#!/usr/bin/env python3
"""Verify v7.0.2 scoped Loon .lsr routing and unified icon directory."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build/candidates/v7.0.1/LoonKit.lcf"
HERE = ROOT / "build/candidates/v7.0.2"
EXPECTED_NEW = {"GitHub", "ChatGPT", "Gemini", "Claude", "Speedtest", "Cloudflare"}
ALLOWED = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "USER-AGENT",
           "IP-CIDR", "IP-CIDR6", "IP-ASN"}
URL = "https://raw.githubusercontent.com/YohakuSama/loonkit/"

def section(content: str, name: str) -> str:
    start = re.search(r"(?m)^\[" + re.escape(name) + r"\]$", content)
    if not start:
        raise ValueError("missing Loon section: "+name)
    tail = content[start.end():]
    end = re.search(r"(?m)^\[[^\]]+\]$", tail)
    return tail[:end.start()] if end else tail

def lines(data: bytes) -> list[str]:
    return [x.strip() for x in data.decode("utf-8-sig").splitlines()
            if x.strip() and not x.lstrip().startswith(("#",";"))]

def parse_rule(rule: str):
    parts = [x.strip() for x in rule.split(",")]
    if len(parts) < 2 or len(parts) > 3 or parts[0] not in ALLOWED or not parts[1]:
        raise ValueError("unsupported rule syntax: "+rule)
    if len(parts)==3 and (not parts[0].startswith("IP-") or parts[2]!="no-resolve"):
        raise ValueError("unsupported optional parameter: "+rule)
    return parts

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def domain_match(domain: str, rule: str) -> bool:
    kind, value, *_ = parse_rule(rule)
    if kind=="DOMAIN":
        return domain==value
    if kind=="DOMAIN-SUFFIX":
        return domain==value or domain.endswith("."+value)
    if kind=="DOMAIN-KEYWORD":
        return value in domain
    return False

def select(domain: str, local: list[str], by_policy: list[tuple[str,list[str]]]) -> str | None:
    for rule in local:
        parts = rule.split(",")
        if parts[0].startswith("DOMAIN") and domain_match(domain,",".join(parts[:2])):
            return parts[2]
    for policy, rules in by_policy:
        if any(domain_match(domain,x) for x in rules if x.startswith(("DOMAIN,","DOMAIN-SUFFIX,","DOMAIN-KEYWORD,"))):
            return policy
    return None

def check() -> dict:
    meta = json.loads((HERE/"candidate_manifest.json").read_text(encoding="utf-8"))
    new = (HERE/"LoonKit.lcf").read_text(encoding="utf-8")
    old = BASE.read_text(encoding="utf-8")
    assert meta["version"]=="v7.0.2"
    assert new.startswith("# LoonKit v7.0.2\n")
    assert meta["policy_group_count"]==39 and meta["remote_rule_count"]==42
    for part in ("General","Proxy","Remote Proxy","Remote Filter","Plugin"):
        if section(old,part)!=section(new,part):
            raise ValueError("unrelated runtime settings modified: "+part)
    gs = [x for x in section(new,"Proxy Group").splitlines() if " = " in x and not x.lstrip().startswith("#")]
    group_names = [x.split("=",1)[0].strip() for x in gs]
    old_groups = [x.split("=",1)[0].strip() for x in section(old,"Proxy Group").splitlines() if " = " in x]
    if len(gs)!=39 or len(set(group_names))!=39 or set(group_names)!=set(old_groups)|EXPECTED_NEW:
        raise ValueError("policy group inventory invalid")
    if any(x.endswith(("自动策略","手动节点","故障策略")) for x in group_names):
        raise ValueError("unrequested regional group")
    base_remote = [x for x in section(old,"Remote Rule").splitlines() if x.startswith("https://")]
    remote = [x for x in section(new,"Remote Rule").splitlines() if x.startswith("https://")]
    if len(base_remote)!=36 or len(remote)!=42:
        raise ValueError("unexpected number of subscriptions")
    if not all(row.startswith(URL+meta["asset_commit"]+"/rules/releases/v7.0.2/") and ".lsr, policy=" in row
               and ", tag=" in row and row.endswith(", enabled=true") for row in remote):
        raise ValueError("remote subscriptions do not share one immutable .lsr asset commit")
    if remote != [URL+meta["asset_commit"]+"/"+r["path"]+", policy="+r["policy"]
                  +", tag="+r["tag"]+", enabled=true" for r in meta["rule_sets"]]:
        raise ValueError("remote ordering or policy differs from manifest")
    if len(meta["rule_sets"])!=42 or len({x["path"] for x in meta["rule_sets"]})!=42:
        raise ValueError("candidate rule sets are duplicated")
    output = {}
    total = 0
    for row in meta["rule_sets"]:
        p = ROOT / row["path"]
        data = p.read_bytes()
        if git_blob_sha(data)!=row["blob_sha"]:
            raise ValueError("rule resource hash drift: "+row["path"])
        rlines = lines(data)
        for item in rlines:
            parse_rule(item)
        if len(rlines)!=len(set(rlines)):
            raise ValueError("exact rule duplication inside "+row["path"])
        output[row["policy"]] = output.get(row["policy"],[])+rlines
        total += len(rlines)
        stem = p.name.removesuffix(".lsr")
        if stem not in EXPECTED_NEW and stem!="AIScoped":
            baseline = ROOT/"rules/releases/v7.0.1"/(stem+".list")
            if baseline.read_bytes()!=data:
                raise ValueError("unchanged service rule drift: "+stem)
    original_ai=lines((ROOT/"rules/releases/v7.0.1/AIScoped.list").read_bytes())
    current_ai=[x for x in meta["rule_sets"] if x["policy"] in {"AI","ChatGPT","Gemini","Claude"}]
    split=[line for row in current_ai for line in lines((ROOT/row["path"]).read_bytes())]
    if any(split.count(x)!=1 for x in original_ai):
        raise ValueError("former AI domains were dropped or duplicated")
    if any(x in output["AI"] for x in output["ChatGPT"]+output["Gemini"]+output["Claude"]):
        raise ValueError("AI general set still owns an independent service rule")
    icon_files = {r["path"] for r in meta["icon_paths"]}
    if len(icon_files)!=40 or not all(re.fullmatch(r"icons/[^/]+\.png",x) for x in icon_files):
        raise ValueError("not all icons are in one directory")
    for img in meta["icon_paths"]:
        payload=(ROOT/img["path"]).read_bytes()
        if git_blob_sha(payload)!=img["blob_sha"]:
            raise ValueError("icon source hash drift: "+img["path"])
        if payload[:8]!=b"\x89PNG\r\n\x1a\n":
            raise ValueError("not a PNG: "+img["path"])
        if int.from_bytes(payload[16:20],"big")!=512 or int.from_bytes(payload[20:24],"big")!=512:
            raise ValueError("icon must be 512x512: "+img["path"])
    for group in group_names:
        line=next(x for x in gs if x.split("=",1)[0].strip()==group)
        expected=URL+meta["asset_commit"]+"/icons/"+({"動畫瘋":"AnimeCrazy"}.get(group,group))+".png"
        if expected not in line:
            raise ValueError("policy icon not pinned in unified directory: "+group)
    local = [x.strip() for x in section(new,"Rule").splitlines() if x.strip() and not x.lstrip().startswith("#")]
    if "GEOIP,CN,DIRECT,no-resolve" not in local or local[-1]!="FINAL,Final":
        raise ValueError("original GEOIP or FINAL disappeared")
    priorities = [(r["policy"],lines((ROOT/r["path"]).read_bytes())) for r in meta["rule_sets"]]
    examples = {
        "chatgpt.com":"ChatGPT", "openai.com":"ChatGPT",
        "gemini.google.com":"Gemini", "aistudio.google.com":"Gemini",
        "claude.ai":"Claude", "anthropic.com":"Claude",
        "openrouter.ai":"AI", "antigravity.google":"AI",
        "copilot.microsoft.com":"AI",
        "copilot-proxy.githubusercontent.com":"AI",
        "github.com":"GitHub", "api.github.com":"GitHub",
        "raw.githubusercontent.com":"Proxy",
        "speedtest.net":"Speedtest", "speed.cloudflare.com":"Speedtest",
        "cloudflare.com":"Cloudflare", "one.one.one":"Cloudflare",
    }
    failures = [(host,want,select(host,local,priorities))
                for host,want in examples.items() if select(host,local,priorities)!=want]
    if failures:
        raise ValueError("effective domain ownership conflicts: "+str(failures))
    return {"version":"v7.0.2", "policy_groups":39,"rule_sets":42,
            "matchers":total,"icons":len(icon_files), "ownership_cases":len(examples)}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--check",action="store_true",required=True)
    p.parse_args()
    print(json.dumps(check(),ensure_ascii=False,indent=2))
