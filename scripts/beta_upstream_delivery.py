#!/usr/bin/env python3
"""Turn bounded routine additions into a pinned, importable DRAFT beta PR.

prepare runs without write credentials on the exact beta checkout. publish runs
from trusted main code in a separate job. No force push, auto merge or main writes.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from beta_github import GitHub, GitHubError, REPOSITORY

ROOT = Path(__file__).resolve().parents[1]
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
VERSION = re.compile(r"(v[0-9]+\.[0-9]+\.[0-9]+-beta\.)([1-9][0-9]*)\Z")
DOMAIN = re.compile(r"DOMAIN,(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,62}\Z")
OWNERS = {"YouTube", "Netflix", "Disney", "PrimeVideo", "TikTok", "Telegram",
          "Whatsapp", "Instagram", "Facebook", "Twitter", "Discord", "Google", "Steam", "HBO",
          "Dazn", "動畫瘋", "Spotify", "Twitch", "Abema", "BBC", "Line", "Reddit", "Linkedin"}
SHARED = ("googleapis.com", "apis.google.com", "appspot.com", "cloudfront.net", "akamaihd.net",
          "akamaized.net", "fastly.net", "windows.net", "blob.core.windows.net", "amazonaws.com",
          "github.io", "pages.dev", "workers.dev", "vercel.app", "stripe.com", "auth0.com",
          "microsoftonline.com", "icloud.com", "apple.com", "paypal.com", "recaptcha.net", "gstatic.com",
          "livekit.cloud", "twilio.com", "githubusercontent.com", "azurewebsites.net",
          "azurefd.net", "azurefd.us", "azureedge.net", "cloudapp.net", "trafficmanager.net",
          "azurecontainer.io", "azure-apim.net", "azurecosmos.net", "azurecosmosdb.com",
          "azurecosmosdb.net", "azurecosmosdb.info", "azuredatabricks.net", "azure-devices.net",
          "akamaiedge.net", "msecnd.net", "live-video.net", "onetrust.com", "cookielaw.org",
          "cdn20.com", "00cdn.com", "ksyungslb.com", "kunlunhuf.com", "kunlunpi.com")
RAW = "https://raw.githubusercontent.com/" + REPOSITORY + "/"
MAX_TOTAL = 30


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def next_version(version):
    hit = VERSION.fullmatch(version)
    if not hit:
        raise ValueError("expected semantic beta version")
    return hit[1] + str(int(hit[2]) + 1)


def effective_conflict(host, group, local, remotes):
    from beta_effective_audit import trace
    route=trace(host,local,remotes)
    cn=trace(host,local,remotes,country='CN')
    if cn['policy'] == 'DIRECT' and route['policy'] != 'DIRECT':
        return 'REGIONAL_SCOPE_REVIEW'
    if route['policy'] != 'Final':
        return 'ALREADY_COVERED' if route['policy'] == group else 'ACTIVE_BETA_OWNER_CONFLICT'
    return None


def prepare(candidate: Path, root: Path = ROOT) -> dict:
    import beta_channel
    import beta_effective_audit
    import beta_upstream_triage
    beta_channel.validate(root)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    subprocess.run(["git", "diff", "--exit-code", "HEAD"], cwd=root, check=True, capture_output=True)
    meta, local, remotes = beta_effective_audit.build(root)
    manifest = json.loads((candidate / "BETA_UPSTREAM_MANIFEST.json").read_text())
    delta = json.loads((candidate / "evidence/FULL_DIFF.json").read_text())
    risks = json.loads((candidate / "evidence/FULL_RISK_AUDIT.json").read_text())
    if manifest.get("baseline_commit") != base or manifest.get("runtime_baseline") is not True:
        raise ValueError("upstream proposal is not based on the exact active beta")
    if manifest.get("version") != next_version(meta["version"]):
        raise ValueError("proposal version must be the next active beta version")
    triage = beta_upstream_triage.evaluate(manifest, delta, risks)
    selected, skipped = {}, {}
    for group, verdict in triage["groups"].items():
        if verdict["status"] != "LOW_RISK_DRAFT_PR_ELIGIBLE_REVIEW_REQUIRED":
            continue
        rows = []
        for rule in delta[group]["added"]:
            host = rule.split(",", 1)[1]
            conflict=effective_conflict(host,group,local,remotes)
            if conflict is None:
                rows.append(rule)
            else:
                skipped[rule] = conflict
        if rows:
            selected[group] = {"rules": sorted(rows), "provenance": {
                row["rule"]: row["source_ids"] for row in risks[group]["additions"] if row["rule"] in rows}}
    return {"schema_version":1, "repository":REPOSITORY, "base_commit":base,
            "base_configuration_sha256":meta["configuration_sha256"], "version":manifest["version"],
            "runtime_baseline":True, "source_integrity_complete":triage["source_integrity_complete"],
            "sources":manifest["source_snapshots"], "source_count":manifest["source_count"],
            "groups":selected, "skipped_effective_matches":skipped,
            "manual_groups":[g for g,v in triage["groups"].items() if v["status"] == "MANUAL_RISK_REVIEW"],
            "full_diff_sha256":digest((candidate / "evidence/FULL_DIFF.json").read_bytes()),
            "created_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}


def validate_plan(plan, meta, profile, catalog):
    from route_diagnostics import Router
    if plan.get("schema_version") != 1 or plan.get("repository") != REPOSITORY:
        raise ValueError("wrong publication plan schema/repository")
    if not HEX40.fullmatch(str(plan.get("base_commit", ""))):
        raise ValueError("exact beta base SHA required")
    if plan.get("runtime_baseline") is not True or plan.get("source_integrity_complete") is not True:
        raise ValueError("complete active-beta source evidence required")
    if digest(profile) != meta["configuration_sha256"] or plan.get("base_configuration_sha256") != digest(profile):
        raise ValueError("tested base profile hash mismatch")
    if plan.get("version") != next_version(meta["version"]):
        raise ValueError("stale or invalid proposed version")
    source_rows = plan.get("sources")
    if not isinstance(source_rows, list) or len(source_rows) != plan.get("source_count"):
        raise ValueError("incomplete source evidence")
    sources = {s["id"]:s for s in source_rows}
    registered = {s["id"]:s for s in catalog["sources"]}
    if len(sources) != len(source_rows) or set(sources) != set(registered):
        raise ValueError("source IDs differ from trusted catalog")
    for sid, source in sources.items():
        if set(source) - {"id", "group", "url", "status", "sha256", "bytes", "fetched_at_utc", "http_etag", "http_last_modified", "expanded_includes"}:
            raise ValueError("unexpected private or unreviewed source metadata")
        if source.get("url") != registered[sid].get("url") or source.get("group") != registered[sid]["group"]:
            raise ValueError("unregistered source identity")
        if not HEX64.fullmatch(str(source.get("sha256", ""))) or source.get("status") not in {"PARSED_FOR_REVIEW", "PARSED_WITH_DOCUMENTED_EXCLUSIONS"}:
            raise ValueError("source hash or retrieval incomplete")
    groups = plan.get("groups")
    if not isinstance(groups, dict) or set(groups) - OWNERS:
        raise ValueError("direct, advertising, sensitive or unknown service owner cannot be automated")
    trusted_router=Router(ROOT)
    total, all_rules = 0, set()
    for group, selection in groups.items():
        additions = selection.get("rules")
        cap = min(10, max(1, int(meta.get("source_group_counts", {}).get(group, 0) * 0.01)))
        if not isinstance(additions, list) or not 1 <= len(additions) <= cap or len(set(additions)) != len(additions):
            raise ValueError("invalid routine addition count")
        if set(selection.get("provenance", {})) != set(additions):
            raise ValueError("missing exact addition provenance")
        if any(s.get("status") != "PARSED_FOR_REVIEW" for s in source_rows if s.get("group") == group):
            raise ValueError("owner sources include lossy normalization")
        for rule in additions:
            if not isinstance(rule, str) or len(rule) > 260 or not DOMAIN.fullmatch(rule):
                raise ValueError("only valid exact public DOMAIN additions may enter automatic draft")
            host = rule.split(",", 1)[1]
            if any(host == value or host.endswith("." + value) for value in SHARED):
                raise ValueError("shared infrastructure needs manual review")
            if any(not trusted_router.match(host,country=code)['predicted_policy'].startswith('Final') for code in ('CN','US')):
                raise ValueError('candidate host already covered by current routing')
            evidence = selection["provenance"][rule]
            if not isinstance(evidence, list) or not evidence or any(s not in sources or sources[s]["group"] != group for s in evidence):
                raise ValueError("rule source owner mismatch")
            if rule in all_rules:
                raise ValueError("cross-owner exact collision")
            all_rules.add(rule)
        total += len(additions)
    if total > MAX_TOTAL:
        raise ValueError("routine batch exceeds total change cap")
    if not HEX64.fullmatch(str(plan.get("full_diff_sha256", ""))):
        raise ValueError("full upstream diff digest missing")
    try:
        created = datetime.fromisoformat(plan["created_at_utc"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - created).total_seconds()
        if not 0 <= age <= 86400:
            raise ValueError("stale or future publication plan")
    except (KeyError, TypeError, ValueError):
        raise ValueError("publication plan requires a real UTC timestamp within 24h") from None
    return total


def create_review_pr(client, branch, base, assets, count, version):
    try:
        return client.post('/pulls',{'base':'beta','head':branch,'draft':True,
            'title':'beta: upstream additions for ' + version,
            'body':'Adds ' + str(count) + ' exact host rules.\n\nBase: ' + base + '\nAssets: ' + assets})
    except GitHubError as error:
        if error.status_code == 403:
            return None
        raise


def review_result(branch, head, assets, count, pr, *, existing=False):
    return {'status':('EXISTING_PR_UNMODIFIED' if pr else 'EXISTING_REVIEW_BRANCH_UNMODIFIED') if existing
            else ('DRAFT_BETA_PR_CREATED' if pr else 'BETA_REVIEW_BRANCH_CREATED'),
            'pull_request':pr['html_url'] if pr else None,
            'compare_url':'https://github.com/' + REPOSITORY + '/compare/beta...' + branch + '?expand=1',
            'branch':branch,'head_sha':head,'asset_commit':assets,'added_rules':count,
            'exact_head_ci_dispatched':True,'review_mode':'DRAFT_PR' if pr else 'MANUAL_PR'}


def publish(plan: dict, client) -> dict:
    head = client.get("/git/ref/heads/beta")
    if not head or head["object"]["sha"] != plan.get("base_commit"):
        raise ValueError("beta moved since preparation; rerun, never force update")
    base = plan["base_commit"]
    profile = client.file("beta/LoonKit.lcf", base)
    meta = json.loads(client.file("build/beta_manifest.json", base))
    catalog = json.loads(client.file("rules/sources.json", base))
    count = validate_plan(plan, meta, profile, catalog)
    if not count:
        return {"status":"NO_ELIGIBLE_RUNTIME_CHANGE", "manual_groups":plan.get("manual_groups", [])}
    key = digest(encoded({"base":base, "groups":{g:s["rules"] for g,s in plan["groups"].items()}}))[:16]
    branch = "automation/beta-upstream-" + key
    existing = client.get("/git/ref/heads/" + branch)
    if existing:
        prs = client.get("/pulls?state=all&head=YohakuSama:" + branch + "&base=beta&per_page=100") or []
        if len(prs) == 1:
            if prs[0].get('state','open') != 'open':
                return {'status':'EXISTING_PR_UNMODIFIED','pull_request':prs[0]['html_url'],'branch':branch,'exact_head_ci_dispatched':False}
            client.post('/actions/workflows/beta-ci.yml/dispatches',{'ref':branch})
            return review_result(branch,existing['object']['sha'],None,count,prs[0],existing=True)
        if prs:
            raise ValueError('existing automation branch has no unique PR; inspect without overwriting')
        current=existing['object']['sha']
        candidate=json.loads(client.file('build/beta_manifest.json',current))
        candidate_profile=client.file('beta/LoonKit.lcf',current)
        update=candidate.get('upstream_update',{})
        if (candidate.get('version') != plan['version'] or update.get('base_commit') != base
                or update.get('selected_additions') != {g:s['rules'] for g,s in plan['groups'].items()}
                or digest(candidate_profile) != candidate.get('configuration_sha256')):
            raise ValueError('existing review branch differs from the prepared candidate')
        assets=candidate['candidate_source_commit']
        pr=create_review_pr(client,branch,base,assets,count,plan['version'])
        client.post('/actions/workflows/beta-ci.yml/dispatches',{'ref':branch})
        return review_result(branch,current,assets,count,pr,existing=pr is None)
    evidence = json.loads(client.file("docs/BETA_ACCEPTANCE_TEMPLATE.json", base))
    if evidence.get("status") != "TEMPLATE_NOT_EVIDENCE" or evidence.get("maintainer_approved") is not False:
        raise ValueError("public acceptance template must never be a release approval")
    commit = client.get("/git/commits/" + base)
    files, entries = {}, {}
    for group, selection in sorted(plan["groups"].items()):
        old_rules = set()
        old = meta.get("upstream_overlays", {}).get(group)
        if old:
            hit = re.fullmatch(re.escape(RAW) + r"([a-f0-9]{40})/(rules/beta/upstream/[A-Za-z0-9._/-]+)", old["uri"])
            if not hit or ".." in hit[2].split("/"):
                raise ValueError("old runtime overlay URL is not a pinned generated resource")
            raw = client.file(hit[2], hit[1])
            if digest(raw) != old["sha256"]:
                raise ValueError("old runtime overlay content changed")
            old_rules = {r for r in raw.decode().splitlines() if r and not r.startswith("#")}
            if any(not DOMAIN.fullmatch(r) for r in old_rules):
                raise ValueError("old overlay contains unsupported rules")
        rules = old_rules | set(selection["rules"])
        if len(rules) > 500:
            raise ValueError("cumulative routine overlay needs manual consolidation")
        filename = "AnimeCrazy" if group == "動畫瘋" else group
        path = "rules/beta/upstream/" + plan["version"] + "/" + filename + ".list"
        raw = ("# LoonKit " + plan["version"] + " routine upstream draft additions; policy " + group + "\n" + "\n".join(sorted(rules)) + "\n").encode()
        files[path] = raw
        entries[group] = {"path":path, "sha256":digest(raw), "matcher_count":len(rules)}

    def tree(base_tree, content):
        return client.post("/git/trees", {"base_tree":base_tree, "tree":[
            {"path":p, "mode":"100644", "type":"blob", "content":b.decode()} for p,b in sorted(content.items())]})["sha"]

    asset_tree = tree(commit["tree"]["sha"], files)
    assets = client.post("/git/commits", {"message":"build(beta): freeze bounded upstream additions before profile pin", "tree":asset_tree, "parents":[base]})["sha"]
    if not HEX40.fullmatch(assets):
        raise ValueError("GitHub did not return a valid immutable asset commit")
    next_meta = copy.deepcopy(meta)
    overlays = next_meta.setdefault("upstream_overlays", {})
    for group, entry in entries.items():
        overlays[group] = {"uri":RAW + assets + "/" + entry["path"], "source_commit":assets,
                           "sha256":entry["sha256"], "matcher_count":entry["matcher_count"]}
    lines = profile.decode().splitlines()
    if lines[0] != "# LoonKit " + meta["version"] + " · BETA TEST ONLY":
        raise ValueError("unrecognized beta entry header")
    lines[0] = "# LoonKit " + plan["version"] + " · BETA TEST ONLY"
    tags = {"Beta-Upstream-" + g for g in overlays}
    lines = [line for line in lines if not any("tag=" + tag + "," in line for tag in tags)]
    position = next(i for i,line in enumerate(lines) if "tag=Beta-AdBlock-Balanced," in line) + 1
    additions = [overlays[g]["uri"] + ", policy=" + g + ", tag=Beta-Upstream-" + g + ", enabled=true" for g in sorted(overlays)]
    lines[position:position] = additions
    next_profile = ("\n".join(lines) + "\n").encode()
    next_meta.update(version=plan["version"], configuration_sha256=digest(next_profile), candidate_source_commit=assets,
                     runtime_remote_count=sum(line.startswith("https://") and ", policy=" in line for line in lines))
    next_meta["acceptance"] = {**meta["acceptance"], "ci":"PENDING_EXACT_CANDIDATE_CHECKS", "device":"NEW_RULE_DELTA_REVIEW_REQUIRED", "promotion":"BLOCKED"}
    next_meta["upstream_update"] = {"base_commit":base, "selected_additions":{g:s["rules"] for g,s in plan["groups"].items()},
        "full_diff_sha256":plan["full_diff_sha256"], "source_snapshots":plan["sources"], "created_at_utc":plan["created_at_utc"]}
    for group, selection in plan["groups"].items():
        next_meta["source_group_counts"][group] += len(selection["rules"])
        tag = "Beta-Upstream-" + group
        source_tags = next_meta.setdefault("source_group_tags", {})
        tags = source_tags.setdefault(group, [])
        # Match the renderer's deterministic order: routine overlay first.
        source_tags[group] = [tag] + [t for t in tags if t != tag]
    if next_meta.get('schema_version') == 2:
        by_uri = {r['uri']:r for r in meta['runtime_resources']}
        for group, item in overlays.items():
            match = re.fullmatch(re.escape(RAW) + r'([a-f0-9]{40})/(rules/beta/upstream/[A-Za-z0-9._/-]+)', item['uri'])
            if not match:
                raise ValueError('routine overlay URI is not a generated immutable resource')
            by_uri[item['uri']] = {**item, 'commit':match[1], 'path':match[2],
                'policy':group, 'tag':'Beta-Upstream-' + group, 'enabled':'true'}
        rows = []
        for line in lines:
            if line.startswith('https://') and ', policy=' in line:
                uri = line.split(',',1)[0]
                record = by_uri[uri].copy()
                record.pop('source_commit',None)
                rows.append(record)
        next_meta['runtime_resources'] = rows
    evidence.update(version=plan["version"], configuration_sha256=digest(next_profile), commit_sha=None)
    review = ('# ' + plan['version'] + ' upstream\n\nBase: ' + base + '\nAssets: ' + assets
              + '\nExact additions: ' + str(count) + '\n\nSources: build/beta_manifest.json\n')
    changed = {"beta/LoonKit.lcf":next_profile, "build/beta_manifest.json":encoded(next_meta),
               "docs/BETA_ACCEPTANCE_TEMPLATE.json":encoded(evidence),
               "docs/beta-upstream/" + plan["version"] + ".md":review.encode()}
    final_tree = tree(asset_tree, changed)
    final = client.post("/git/commits", {"message":"beta: pin " + plan["version"] + " upstream draft and reset acceptance", "tree":final_tree, "parents":[assets]})["sha"]
    # Re-check the base immediately before making the branch reachable.
    if client.get("/git/ref/heads/beta")["object"]["sha"] != base:
        raise ValueError("beta moved during build; no branch or PR published")
    client.post("/git/refs", {"ref":"refs/heads/" + branch, "sha":final})
    pr=create_review_pr(client,branch,base,assets,count,plan['version'])
    # GITHUB_TOKEN-created PRs do not trigger normal pull_request workflows.
    # Explicit dispatch is required; beta-ci.yml must exist on default main.
    client.post("/actions/workflows/beta-ci.yml/dispatches", {"ref":branch})
    return review_result(branch,final,assets,count,pr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("publish")
    p.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        result = prepare(args.candidate)
        if args.output.resolve().is_relative_to(ROOT):
            raise ValueError("publication plans must be outside the checkout")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(encoded(result))
        print(json.dumps({"status":"PLAN_READY" if result["groups"] else "NO_ROUTINE_ADDITIONS", "groups":list(result["groups"])}))
    else:
        if args.plan.stat().st_size > 512 * 1024:
            raise ValueError("publication plan too large")
        result = publish(json.loads(args.plan.read_text()), GitHub(os.environ.get("GITHUB_TOKEN", "")))
        link=result.get('pull_request') or result.get('compare_url')
        if link and os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as summary:
                summary.write('## Beta candidate\n\n[Review update](' + link + ')\n\nCommit: `' + result.get('head_sha','') + '`\n')
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
