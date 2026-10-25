#!/usr/bin/env python3
"""Static owner-of-domain audit against the 42 frozen v7.0.2 Loon subscriptions."""
from __future__ import annotations
import argparse
import ipaddress
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audit_v702 import lines, section

DOMESTIC_AI=("deepseek.com","deepseeksvc.com","kimi.ai","moonshot.cn","kimichat.com",
"zhipuai.cn","chatglm.cn","bigmodel.cn","doubao.com","coze.cn","minimaxi.com",
"hailuoai.com","hailuoai.video","baichuan-ai.com","01.ai","lingyiwanwu.com",
"stepfun.com","sensenova.cn","sparkchain.cn")
BOUNDARIES={
"chatgpt.com":"ChatGPT","openai.com":"ChatGPT","claude.ai":"Claude",
"anthropic.com":"Claude","gemini.google.com":"Gemini",
"antigravity.google":"AI","githubcopilot.com":"AI",
"models.github.ai":"AI","grok.com":"AI","x.ai":"AI",
"www.youtube.com":"YouTube","googlevideo.com":"YouTube",
"docs.google.com":"Google","drive.google.com":"Google",
"aliexpress.com":"DIRECT","tiktok.com":"TikTok","douyin.com":"DIRECT",
"github.com":"GitHub","raw.githubusercontent.com":"Proxy",
"speed.cloudflare.com":"Speedtest","cloudflare.com":"Cloudflare",
"onedrive.com":"Microsoft","sharepoint.com":"Microsoft",
"twitter.com":"Twitter","discord.com":"Discord",
"telegram.org":"Telegram","apple.com":"Apple","testflight.apple.com":"Apple",
}

def owner(host:str, rules:dict, order:list, local:list):
    for line in local:
        p=line.split(",")
        if len(p)>=3 and p[0] in ("DOMAIN","DOMAIN-SUFFIX","DOMAIN-KEYWORD") and matches(host,p):
            return p[2]
    for row in order:
        for line in rules[row["path"]]:
            p=line.split(",")
            if p[0] in ("DOMAIN","DOMAIN-SUFFIX","DOMAIN-KEYWORD") and matches(host,p):
                return row["policy"]
    return None

def matches(host,p):
    k,s=p[:2]
    if k=="DOMAIN": return host==s
    if k=="DOMAIN-SUFFIX": return host==s or host.endswith("."+s)
    if k=="DOMAIN-KEYWORD": return s in host
    return False

def scan(path:Path):
    m=json.loads((path/"candidate_manifest.json").read_text())
    profile=(path/"LoonKit.lcf").read_text()
    order=m["rule_sets"]
    rules={x["path"]:lines((ROOT/x["path"]).read_bytes()) for x in order}
    local=[x.strip() for x in section(profile,"Rule").splitlines() if x.strip() and not x.lstrip().startswith("#")]
    domestic={s:owner(s,rules,order,local) for s in DOMESTIC_AI}
    sample={s:{"actual":owner(s,rules,order,local),"expected":want} for s,want in BOUNDARIES.items()}
    return {"domestic_ai":domestic,"sample_ownership":sample,
            "unexpected":{s:x for s,x in sample.items() if x["actual"]!=x["expected"]},
            "policy_order":[x["policy"] for x in order],
            "total_matchers":sum(len(rules[x["path"]]) for x in order)}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--candidate",default="build/candidates/v7.0.2")
    a=p.parse_args()
    print(json.dumps(scan(ROOT/a.candidate),indent=2,ensure_ascii=False))
