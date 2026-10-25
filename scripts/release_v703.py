"""Read-only verification of the immutable v7.0.3 formal Loon release."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[1]
VERSION="v7.0.3"
EXPECTED_OLD="a5c0fb40987bf8079ed84167702593d5dd8ce631a03e3df704be09e3578d87b0"
SHA=re.compile(r"[0-9a-f]{40}\Z")
RAW="https://raw.githubusercontent.com/YohakuSama/loonkit/"

def digest(data): return hashlib.sha256(data).hexdigest()
def section(content,name):
    start=re.search(r"(?m)^\["+re.escape(name)+r"\]$",content)
    if not start:raise ValueError("missing section "+name)
    tail=content[start.end():]
    end=re.search(r"(?m)^\[[^]]+\]$",tail)
    return tail[:end.start()] if end else tail

def check(remote:bool=False,root:Path=ROOT)->dict:
    from verify_release import check_public_checksums
    from reviewed_release import validate_records
    from audit_v702 import lines,parse_rule
    from audit_upstream_703 import scan
    spec=json.loads((root/"build/release_spec.json").read_text())
    meta=json.loads((root/"build/release_manifest.json").read_text())
    candidate=json.loads((root/"build/candidates/v7.0.3/candidate_manifest.json").read_text())
    profile=(root/"LoonKit.lcf").read_bytes()
    text=profile.decode("utf-8")
    old=(root/"build/baselines/v7.0.0/LoonKit.lcf").read_bytes()
    previous=json.loads((root/"build/baselines/v7.0.0/release_manifest.json").read_text())
    asset=spec.get("release_assets_commit")
    if (spec.get("stable_release_version")!=VERSION or meta.get("label")!=VERSION
        or not SHA.fullmatch(str(asset))
        or digest(old)!=EXPECTED_OLD
        or previous["label"]!="v7.0.0"
        or previous["profile_sha256"]!={"LoonKit.lcf":EXPECTED_OLD}):
        raise ValueError("former or current publication metadata invalid")
    if profile!=(root/"build/candidates/v7.0.3/LoonKit.lcf").read_bytes():
        raise ValueError("production must be bit-identical to reviewed candidate")
    if not text.startswith("# LoonKit v7.0.3\n") or meta["profile_sha256"]!={"LoonKit.lcf":digest(profile)}:
        raise ValueError("current profile SHA256/header mismatch")
    if candidate.get("asset_commit")!=asset or candidate["profile_sha256"]!=digest(profile):
        raise ValueError("candidate assets or profile hash drifted")
    if len(meta["runtime_resources"])!=43 or meta["runtime_resources"]!=candidate["rule_sets"]:
        raise ValueError("the 43 frozen remote subscriptions do not match released manifest")
    if any((row["commit"]!=asset or not row["path"].startswith("rules/releases/v7.0.3/")
            or not row["path"].endswith(".lsr") or row["enabled"]!="true"
            or row["uri"]!=RAW+asset+"/"+row["path"]) for row in meta["runtime_resources"]):
        raise ValueError("non-immutable or non-native ruleset URL")
    checked=validate_records(profile,meta["runtime_resources"],root,remote=remote)
    count=sum(r["matcher_count"] for r in checked)
    if (count!=meta["remote_rule_count"] or count!=meta["runtime_rule_matcher_count"] 
            or count!=candidate["matcher_count"] or meta["remote_subscription_count"]!=43):
        raise ValueError("ruleset checksum/count inconsistency")
    icon_lines=[x for x in section(text,"Proxy Group").splitlines() if " = " in x]
    if len(icon_lines)!=39 or len({x.split("=",1)[0].strip() for x in icon_lines})!=39:
        raise ValueError("invalid policy group count")
    for line in icon_lines:
        match=re.search(r"img-url\s*=\s*(\S+)",line)
        if not match or not match.group(1).startswith(RAW+asset+"/icons/"):
            raise ValueError("icon not pinned into unified directory")
        if not (root/"icons"/match.group(1).rsplit("/",1)[-1]).is_file():
            raise ValueError("missing PNG from unified icon directory")
    for name in ("General","Proxy","Remote Proxy","Remote Filter","Host","Plugin"):
        if section(text,name)!=section(old.decode(),name):
            raise ValueError("protected runtime section changed: "+name)
    rules=section(text,"Rule")
    if "GEOIP,CN,DIRECT,no-resolve" not in rules or "FINAL,Final" not in rules:
        raise ValueError("local geoip or FINAL changed")
    v702=(root/"build/candidates/v7.0.2/LoonKit.lcf").read_text()
    if rules!=section(v702,"Rule"):
        raise ValueError("unreviewed local rule changes")
    for row in checked:
        content=lines((root/row["path"]).read_bytes())
        if len(content)!=len(set(content)):raise ValueError("duplicate matchers inside "+row["path"])
        for line in content:parse_rule(line)
        if any(line.startswith(("AND,","OR,","NOT,")) for line in content):
            raise ValueError("experimental unsupported composite selector")
    by_path={row["path"].rsplit("/",1)[-1]:row for row in checked}
    baseline=previous["runtime_resources"]
    if by_path["AdBlockBalanced.lsr"]["sha256"] != next(x["sha256"] for x in baseline if x["policy"]=="AdBlock"):
        raise ValueError("adblock payload changed outside scope")
    china=lines((root/by_path["ChinaDirect.lsr"]["path"]).read_bytes())
    if any(x in china for x in ("DOMAIN-SUFFIX,aliexpress.com","DOMAIN,lazada.com","DOMAIN-SUFFIX,lazada.com","DOMAIN-SUFFIX,daraz.com")):
        raise ValueError("foreign commerce still collides with ChinaDirect")
    result=scan(root/"build/candidates/v7.0.3")
    for host,want in (("aliexpress.com","Proxy"),("lazada.com","Proxy"),("daraz.com","Proxy"),
                      ("githubcopilot.com","AI"),("gemini.google.com","Gemini"),
                      ("claude.ai","Claude"),("speed.cloudflare.com","Speedtest")):
        # The scan includes static key services; this calls the same parser for additions.
        from audit_upstream_703 import owner
        orders=candidate["rule_sets"]
        allrules={row["path"]:lines((root/row["path"]).read_bytes()) for row in orders}
        local=[x.strip() for x in rules.splitlines() if x.strip() and not x.strip().startswith("#")]
        if owner(host,allrules,orders,local)!=want:
            raise ValueError("cross policy domain mismatch: "+host+" -> "+want)
    if result["unexpected"] and any(name not in {"aliexpress.com"} for name in result["unexpected"]):
        raise ValueError("preserved service routing regressed: "+str(result["unexpected"]))
    check_public_checksums(root,meta,spec)
    gate=json.loads((root/"docs/RELEASE_OWNER_DECISION_v7.0.3.json").read_text())
    if gate.get("decision")!="OWNER_REQUESTED_FORMAL_PUBLICATION" or gate.get("release_profile_sha256")!=digest(profile):
        raise ValueError("publication decision not scoped to frozen candidate")
    return {"version":VERSION,"asset_commit":asset,"rule_sets":43,"matchers":count,
            "strategy_groups":39,"icon_files":40,"remote_checked":remote,
            "profile_sha256":digest(profile)}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--check",action="store_true",required=True)
    p.add_argument("--remote",action="store_true")
    args=p.parse_args()
    print(json.dumps(check(remote=args.remote),sort_keys=True))
