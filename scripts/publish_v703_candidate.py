#!/usr/bin/env python3
"""Create a pinned v7.0.3 Loon formal release from the reviewed v7.0.2 candidate."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
VERSION="v7.0.3"
ASSET_DIR=ROOT/"rules/releases/v7.0.3"
TARGET=ROOT/"build/candidates/v7.0.3"
ORIGIN=ROOT/"build/candidates/v7.0.2/LoonKit.lcf"
RAW="https://raw.githubusercontent.com/YohakuSama/loonkit/"
SOURCE_SHA="47fa36ef0fcbfb9b664bac6fa2f4e574b6107b0f"
EXEMPT={"AdBlockBalanced.lsr"}
SPECIAL=("Proxy","Auto","Fallback","AdBlock","Final")
AI=("AI","ChatGPT","Gemini","Claude")
SERVICES=("GitHub","Google","Microsoft","Apple","Cloudflare","Speedtest")
STREAM=("YouTube","Netflix","Disney","PrimeVideo","Spotify","TikTok","Twitch","HBO","Abema","動畫瘋","Dazn","BBC","Bilibili")
SOCIAL=("Telegram","Whatsapp","Instagram","Facebook","Twitter","Discord","Line","Reddit","Linkedin")
OTHER=("Steam","Paypal")
GROUP_ORDER=SPECIAL+AI+SERVICES+STREAM+SOCIAL+OTHER
FOREIGN_COMMERCE=("aliexpress.com","lazada.com","daraz.com")
LOCAL_EXCEPTIONS=("raw.githubusercontent.com",)

def sha(data:bytes)->str: return hashlib.sha256(data).hexdigest()
def dump(obj):return json.dumps(obj,ensure_ascii=False,indent=2)+"\n"
def save(path:Path,content:bytes|str):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(content.encode("utf-8") if isinstance(content,str) else content)

def rule_lines(data:bytes|str)->list[str]:
    if isinstance(data,bytes): data=data.decode("utf-8")
    return [line.strip() for line in data.splitlines() if line.strip() and not line.lstrip().startswith(("#",";"))]

def profile_section(text:str,name:str):
    match=re.search(r"(?m)^\["+re.escape(name)+r"\]$",text)
    if not match: raise ValueError("missing "+name)
    end=re.search(r"(?m)^\[[^]]+\]$",text[match.end():])
    return text[match.end(): match.end()+end.start() if end else len(text)]

def replace_section(text:str,name:str,new_content:str)->str:
    match=re.search(r"(?m)^\["+re.escape(name)+r"\]$",text)
    if not match: raise ValueError("section missing "+name)
    tail=text[match.end():]
    end=re.search(r"(?m)^\[[^]]+\]$",tail)
    finish=match.end()+end.start() if end else len(text)
    return text[:match.end()]+"\n"+new_content.rstrip()+"\n\n"+text[finish:]

def unique_rows(old:str):
    result={}
    for line in profile_section(old,"Remote Rule").splitlines():
        if not line.startswith(RAW):continue
        url, *args=line.split(",")
        kv={x.split("=",1)[0].strip():x.split("=",1)[1].strip() for x in args}
        filename=url.rsplit("/",1)[1]
        if not filename.endswith(".lsr"):raise ValueError("bad old resource file "+filename)
        result[filename]=(kv["policy"],kv["tag"])
    if len(result)!=42:raise ValueError("old 42 rows changed")
    return result

def prepared(old:str,asset_sha:str)->tuple[str,list[dict]]:
    if not re.fullmatch("[0-9a-f]{40}",asset_sha):raise ValueError("invalid fixed asset sha")
    profile=old.replace("# LoonKit v7.0.2","# LoonKit v7.0.3",1)
    original=unique_rows(old)
    original["DomesticAI.lsr"]=("DIRECT","Our-DomesticAI")
    original_order=list(original)
    # Explicitly route domestic-only model endpoints before the foreign AI groups.
    priority=["AdBlockBalanced.lsr","DomesticCore.lsr","DomesticSupplement.lsr",
              "SteamCN.lsr","DomesticAI.lsr","ChatGPT.lsr","Gemini.lsr",
              "Claude.lsr","AIScoped.lsr","GitHub.lsr","Speedtest.lsr",
              "Cloudflare.lsr"]
    original_order=priority+[name for name in original_order if name not in priority]
    if len(original_order)!=43 or len(set(original_order))!=43:
        raise ValueError("policy ordering not unique")
    rows=[]
    for name in original_order:
        policy,tag=original[name]
        path="rules/releases/v7.0.3/"+name
        data=(ROOT/path).read_bytes()
        rules=rule_lines(data)
        if not rules or len(rules)!=len(set(rules)):
            raise ValueError("empty or internally duplicated rule file: "+name)
        rows.append({"uri":RAW+asset_sha+"/"+path,"commit":asset_sha,"path":path,
          "policy":policy,"tag":tag,"enabled":"true","sha256":sha(data),
          "matcher_count":len(rules)})
    remote="\n".join(f'{row["uri"]}, policy={row["policy"]}, tag={row["tag"]}, enabled=true' for row in rows)
    profile=replace_section(profile,"Remote Rule",remote)
    definition={}
    for line in profile_section(profile,"Proxy Group").splitlines():
        if " = " in line and not line.strip().startswith("#"):
            name=line.split(" = ",1)[0].strip()
            if name in definition:raise ValueError("duplicate policy "+name)
            definition[name]=line
    if set(definition)!=set(GROUP_ORDER) or len(definition)!=39:
        raise ValueError("unexpected group list: "+str(set(definition)^set(GROUP_ORDER)))
    # Existing group choices remain verbatim; reorder for readable service classification.
    group_lines=[]
    for block in (SPECIAL,AI,SERVICES,STREAM,SOCIAL,OTHER):
        group_lines.extend(definition[x] for x in block)
        group_lines.append("")
    group="\n".join(group_lines)
    # All old icons are already 512x512 in unified icons root.
    old_ref=re.search(r"https://raw\.githubusercontent\.com/YohakuSama/loonkit/([0-9a-f]{40})/icons/",group)
    if not old_ref:raise ValueError("missing icon ref")
    group=group.replace(RAW+old_ref.group(1)+"/icons/",RAW+asset_sha+"/icons/")
    profile=replace_section(profile,"Proxy Group",group)
    if len(re.findall(r"\bimg-url\s*=\s*"+re.escape(RAW+asset_sha+"/icons/"),profile))!=39:
        raise ValueError("39 policy group images required")
    if "GEOIP,CN,DIRECT,no-resolve" not in profile_section(profile,"Rule"):
        raise ValueError("original no-resolve GEOIP lost")
    if "FINAL,Final" not in profile_section(profile,"Rule"):
        raise ValueError("FINAL lost")
    return profile,rows

def prepare_assets()->dict:
    path=ASSET_DIR/"ChinaDirect.lsr"
    original=(ROOT/"rules/releases/v7.0.2/ChinaDirect.lsr").read_text(encoding="utf-8")
    current=path.read_text(encoding="utf-8")
    foreign=set(FOREIGN_COMMERCE)
    removed=[]
    lines=[]
    for line in original.splitlines():
        fields=line.strip().split(",")
        if len(fields)>=2 and fields[0] in ("DOMAIN","DOMAIN-SUFFIX") and fields[1] in foreign:
            removed.append(line)
            continue
        lines.append(line)
    updated="\n".join(lines)+"\n"
    if not removed or not any("aliexpress.com" in s for s in removed):
        raise ValueError("expected reviewed foreign-commerce conflict absent from ChinaDirect")
    save(path,updated)
    if any(line.strip() in updated.splitlines() for line in removed):
        raise ValueError("excluded foreign commerce remains in direct rules")
    print(dump({"removed_from_ChinaDirect":removed,"original_matchers":len(rule_lines(original)),
                "updated_matchers":len(rule_lines(updated))}))
    return {"removed":removed}

def finish(asset_sha:str)->dict:
    source=ORIGIN.read_text(encoding="utf-8")
    content,rows=prepared(source,asset_sha)
    version_sha=sha(content.encode())
    old=(ROOT/"LoonKit.lcf").read_bytes()
    old_sha=sha(old)
    if old_sha!="a5c0fb40987bf8079ed84167702593d5dd8ce631a03e3df704be09e3578d87b0":
        raise ValueError("former published v7.0.0 profile changed")
    old_spec=json.loads((ROOT/"build/release_spec.json").read_text())
    old_meta=json.loads((ROOT/"build/release_manifest.json").read_text())
    if old_spec["stable_release_version"]!="v7.0.0" or old_meta["label"]!="v7.0.0":
        raise ValueError("unexpected prior published metadata")
    if len(rows)!=43: raise ValueError("wrong rule subscription count")
    total=sum(x["matcher_count"] for x in rows)
    save(TARGET/"LoonKit.lcf",content)
    save(ROOT/"LoonKit.lcf",content)
    for p,data in (("LoonKit.lcf",old),("release_manifest.json",dump(old_meta)),
                   ("release_spec.json",dump(old_spec))):
        save(ROOT/"build/baselines/v7.0.0"/p,data)
    meta=copy.deepcopy(old_meta)
    meta.update(label=VERSION,profile_sha256={"LoonKit.lcf":version_sha},
                runtime_resources=rows,runtime_rule_count=43,
                remote_subscription_count=43,remote_rule_count=total,
                runtime_rule_matcher_count=total,
                runtime_change={"version":VERSION,"runtime_semantics":"SERVICE_CLASSIFICATION_UPDATE",
                                "new_policy_groups":6,"new_subscriptions":7,
                                "dns_tun":"UNCHANGED","adblock":"UNCHANGED"})
    meta["previous_release"]={"version":"v7.0.0","profile_sha256":old_sha,
       "commit":"04b7f0712ba9c48945397ac8e865ef7ecd9c0859"}
    meta["maintainer_approval"]="USER_REQUESTED_V703_FORMAL_PUBLICATION_2026_10_25"
    meta["device_test"]="NOT_CLAIMED"
    save(ROOT/"build/release_manifest.json",dump(meta))
    spec=copy.deepcopy(old_spec)
    spec["stable_release_version"]=VERSION
    spec["release_gate_file"]="docs/RELEASE_OWNER_DECISION_v7.0.3.json"
    spec["release_rules_dir"]="rules/releases/v7.0.3"
    spec["release_assets_commit"]=asset_sha
    spec["reviewed_auxiliary_commit"]=asset_sha
    spec["previous_formal_profile_sha256"]=old_sha
    spec["previous_formal_profile_path"]="build/baselines/v7.0.0/LoonKit.lcf"
    spec["previous_formal_manifest_path"]="build/baselines/v7.0.0/release_manifest.json"
    spec["historical_profile_sha256"]["v7.0.0"]=old_sha
    active="\n".join(line for line in content.splitlines()
       if line.strip() and not line.lstrip().startswith("#"))+"\n"
    spec["current_runtime_directives_sha256"]=sha(active.encode("utf-8"))
    save(ROOT/"build/release_spec.json",dump(spec))
    decision={"schema_version":1,"version":VERSION,
        "decision":"OWNER_REQUESTED_FORMAL_PUBLICATION","asset_commit":asset_sha,
        "release_profile_sha256":version_sha,
        "former_version":"v7.0.0","former_profile_sha256":old_sha,
        "real_device_test":"NOT_ATTESTED","ruleset_count":43,
        "strategy_group_count":39,"source_coverage":"pinned LoonKit, o-ocn/loon-rules GPL-2.0 and blackmatrix7"}
    save(ROOT/"docs/RELEASE_OWNER_DECISION_v7.0.3.json",dump(decision))
    save(ROOT/"release/SHA256SUMS.v7.0.3",version_sha+"  LoonKit.lcf\n")
    save(ROOT/"docs/RELEASE_CHECKSUM_v7.0.3.md","# LoonKit v7.0.3\n\n"+version_sha+"  LoonKit.lcf\n")
    cache=json.loads((ROOT/"build/candidates/v7.0.2/candidate_manifest.json").read_text())
    cm={"schema_version":2,"version":VERSION,"asset_commit":asset_sha,
        "profile_sha256":version_sha,"rule_sets":rows,
        "matcher_count":total,"policy_group_count":39,"remote_rule_count":43,
        "icon_count":40,"parent_candidate":"v7.0.2",
        "adblock_content_sha256":next(x["sha256"] for x in rows if x["policy"]=="AdBlock"),
        "known_cross_policy_boundaries":{
         "AI_over_GitHub":"githubcopilot.com models.github.ai",
         "Gemini_over_Google":"gemini.google.com robinfrontend-pa.googleapis.com",
         "YouTube_over_Google":"youtube.com googlevideo.com",
         "Speedtest_over_Cloudflare":"speed.cloudflare.com",
         "Proxy_over_ChinaDirect":"aliexpress.com lazada.com daraz.com"}}
    save(TARGET/"candidate_manifest.json",dump(cm))
    # Update only status references describing the active production configuration.
    for p in ("README.md","rules/README.md"):
        file=ROOT/p
        text=file.read_text(encoding="utf-8")
        if "v7.0.0" in text:
            file.write_text(text.replace("v7.0.0",VERSION),encoding="utf-8")
    return {"version":VERSION,"asset_commit":asset_sha,"profile_sha256":version_sha,
            "rule_sets":len(rows),"matchers":total,"groups":39,"icons":40}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--prepare-assets",action="store_true")
    p.add_argument("--finalize",action="store_true")
    p.add_argument("--asset-commit")
    args=p.parse_args()
    if args.prepare_assets:
        prepare_assets()
    elif args.finalize and args.asset_commit:
        print(dump(finish(args.asset_commit)))
    else:
        p.error("use --prepare-assets or --finalize --asset-commit SHA")
