#!/usr/bin/env python3
"""Generate the reviewed release and next beta from frozen inputs."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
from beta_channel import ROOT, content_rules
from reviewed_release import records, render_beta
from release_v658 import render, verify


def write(asset_commit, root=ROOT):
    def read(path): return json.loads((root/path).read_text())
    def save(path, value):
        (root/path).parent.mkdir(parents=True,exist_ok=True)
        (root/path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    digest=lambda raw:hashlib.sha256(raw).hexdigest()
    profile=render(asset_commit,root)
    (root/'LoonKit.lcf').write_bytes(profile)
    spec=read('build/baselines/v6.5.7/release_spec.json')
    spec.update(stable_release_version='v6.5.8',status='REVIEWED_CANDIDATE_PENDING_PR_CI',
        release_gate_file='docs/RELEASE_OWNER_DECISION_v6.5.8.json',reviewed_assets_commit=asset_commit,
        previous_formal_profile_sha256='9dbcb5bff0cae6be233053e13b464176a0af4ad714efd27b3fa290f3c86ee84b',
        previous_formal_profile_path='build/baselines/v6.5.7/LoonKit.lcf',
        previous_formal_manifest_path='build/baselines/v6.5.7/release_manifest.json',
        current_runtime_directives_sha256=digest(('\n'.join(x for x in profile.decode().splitlines() if x.strip() and not x.lstrip().startswith('#'))+'\n').encode()))
    spec['historical_profile_sha256']['v6.5.7']=spec['previous_formal_profile_sha256']
    spec.pop('warning',None)
    save('build/release_spec.json',spec)
    rollback='a67828e6efbe6c4f6e19be4d78abfe28b1cb2953'
    meta=read('build/baselines/v6.5.7/release_manifest.json')
    meta.update(label='v6.5.8',reviewed_recipe='rules/reviewed/v6.5.8/decisions.json',
        reviewed_assets_commit=asset_commit,profile_sha256={'LoonKit.lcf':digest(profile)},
        stage='REVIEWED_RELEASE_PENDING_CI',runtime_resources=records(profile,root),
        maintainer_approval='OWNER_REQUESTED_PUBLICATION_2026_10_25',device_test='NOT_RECORDED',
        old_main_rollback_commit=rollback,approved_runtime_directives_sha256=spec['current_runtime_directives_sha256'])
    count=sum(r['matcher_count'] for r in meta['runtime_resources'])
    meta.update(runtime_rule_count=len(meta['runtime_resources']),remote_subscription_count=len(meta['runtime_resources']),
        remote_rule_count=count,runtime_rule_matcher_count=count)
    meta['previous_release']={'version':'v6.5.7','profile_sha256':spec['previous_formal_profile_sha256'],'commit':rollback}
    meta['runtime_change']={'routing':'GEOIP_SCOPED_CN_AND_SERVICE_OVERSEAS','removed_user_agent_rules':50,'dns_bootstrap':'ALIDNS_HOST_MAPPING'}
    meta['publication']={'status':'PENDING_EXACT_PR_HEAD_CI','rollback_main_commit_sha':rollback,'published_main_commit_sha':None}
    by_tag={r['tag']:r for r in meta['runtime_resources']}
    meta['source_group_counts']={g:len(set().union(*(set(content_rules((root/by_tag[t]['path']).read_bytes())) for t in tags))) for g,tags in meta['source_group_tags'].items()}
    save('build/release_manifest.json',meta)
    (root/'release/SHA256SUMS.v6.5.8').write_text(digest(profile)+'  LoonKit.lcf\n')
    (root/'docs/RELEASE_CHECKSUM_v6.5.8.md').write_text('# LoonKit v6.5.8\n\n```text\n'+digest(profile)+'  LoonKit.lcf\n```\n')
    save(spec['release_gate_file'],{'schema_version':1,'version':'v6.5.8',
        'decision':'OWNER_REQUESTED_AUDIT_FIXES_AND_PUBLICATION','received_date':'2026-10-25',
        'release_profile_sha256':digest(profile),'protected_directive':'GEOIP,CN,DIRECT,no-resolve',
        'dns_provider':'AliDNS','apply_to_future_versions':False,'require_actual_pr_head_ci':True,'require_main_raw_verification':True})
    base='build/baselines/v6.5.8/'
    (root/base).mkdir(exist_ok=True)
    (root/(base+'LoonKit.lcf')).write_bytes(profile)
    save(base+'release_manifest.json',meta)
    beta=read('build/baselines/v6.5.8-beta.1/beta_manifest.json')
    beta.update(version='v6.5.9-beta.1',status='DEVELOPMENT_CHANNEL',stable_release='v6.5.8',
        production_baseline=rollback,candidate_source_commit=asset_commit,immutable_overlay_commit=asset_commit,
        foundation_profile_path=base+'LoonKit.lcf',foundation_profile_sha256=digest(profile),
        foundation_manifest_path=base+'release_manifest.json',foundation_manifest_sha256=digest((root/(base+'release_manifest.json')).read_bytes()))
    beta['source_group_tags']=copy.deepcopy(meta['source_group_tags'])
    beta['source_group_counts']=copy.deepcopy(meta['source_group_counts'])
    beta['upstream_overlays']={}
    beta.pop('limitations',None)
    cn=by_tag['Beta-ChinaDirect-Scoped']
    beta['china_direct']={**cn,'source_commit':cn['commit']}
    bp,beta=render_beta(beta,root)
    (root/'beta/LoonKit.lcf').write_bytes(bp)
    save('build/beta_manifest.json',beta)
    evidence=read('docs/BETA_ACCEPTANCE_TEMPLATE.json')
    if evidence['status'] != 'TEMPLATE_NOT_EVIDENCE' or evidence['maintainer_approved']:
        raise ValueError('expected an empty public acceptance template')
    evidence.update(version=beta['version'],configuration_sha256=beta['configuration_sha256'],commit_sha=None,rollback_commit_sha=rollback)
    save('docs/BETA_ACCEPTANCE_TEMPLATE.json',evidence)
    return {'version':'v6.5.8','sha256':digest(profile),'beta_sha256':digest(bp),'resources':len(meta['runtime_resources']),'matchers':count}


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--write',action='store_true')
    g.add_argument('--check',action='store_true')
    p.add_argument('--asset-commit')
    args=p.parse_args()
    if args.write and not args.asset_commit:p.error('--write requires --asset-commit')
    print(json.dumps(write(args.asset_commit) if args.write else verify(),sort_keys=True))
