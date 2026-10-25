#!/usr/bin/env python3
"""Deterministic, reviewed deltas over a frozen release; never fetch upstream."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen
from loon_resources import ROOT, URI, remote_entries, content_rules, section

RECIPE = 'rules/reviewed/v6.5.7/decisions.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(root, path):
    return json.loads((root / path).read_text())


def render_rules(root=ROOT):
    spec = read_json(root, RECIPE)
    if spec['schema_version'] != 1:
        raise ValueError('unsupported reviewed recipe')
    output = {}
    for row in spec['rules']:
        raw = (root / row['source_path']).read_bytes()
        if sha(raw) != row['source_sha256']:
            raise ValueError('reviewed source changed: ' + row['tag'])
        rules = content_rules(raw)
        if any(rules.count(x) != 1 for x in row['remove_exact']):
            raise ValueError('reviewed exclusion absent or duplicated')
        for kind, count in row['remove_kinds'].items():
            if sum(x.startswith(kind + ',') for x in rules) != count:
                raise ValueError('reviewed kind exclusion changed')
        remaining = [x for x in rules if x not in row['remove_exact'] and x.split(',')[0] not in row['remove_kinds']]
        if set(row['add']) & set(remaining) or len(set(row['add'])) != len(row['add']):
            raise ValueError('reviewed additions are duplicates')
        remaining += row['add']
        output[row['output_path']] = ('# LoonKit ' + spec['version'] + ' reviewed ' + row['owner'] + ' rules; see ' + RECIPE + '\n' + '\n'.join(remaining) + '\n').encode()
    return output


def records(profile, root=ROOT):
    # Read each immutable resource once, then derive both digest and count.
    result = []
    for row in remote_entries(profile.decode()):
        raw = (root / row['path']).read_bytes()
        result.append({**row, 'sha256': sha(raw),
                       'matcher_count': len(content_rules(raw))})
    return result


def validate_records(profile, expected, root=ROOT, remote=False):
    actual = records(profile, root)
    if actual != expected:
        raise ValueError('resource bytes, ordering, ownership or immutable refs differ')
    if remote:
        def check(row):
            with urlopen(row['uri'], timeout=35) as response:
                if response.geturl() != row['uri']:
                    raise ValueError('immutable resource redirected')
                raw = response.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024 or sha(raw) != row['sha256']:
                raise ValueError('immutable remote bytes differ: ' + row['path'])
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(check, actual))
    return actual


def render(asset_commit, root=ROOT):
    if not re.fullmatch('[a-f0-9]{40}', asset_commit):
        raise ValueError('freeze assets at a real commit before profile generation')
    spec = read_json(root, RECIPE)
    base = (root / spec['base_profile_path']).read_bytes()
    if sha(base) != spec['base_profile_sha256']:
        raise ValueError('frozen formal template changed')
    replacements = {r['tag']:r for r in spec['rules']}
    result = []
    seen = set()
    for line in base.decode().splitlines():
        if line.startswith('# LoonKit '):
            line = '# LoonKit ' + spec['version']
        if line.startswith('https://') and ', policy=' in line:
            old, *options = line.split(',')
            props = dict(x.strip().split('=',1) for x in options)
            tag = props['tag']
            if tag in replacements:
                seen.add(tag)
                line = 'https://raw.githubusercontent.com/YohakuSama/loonkit/' + asset_commit + '/' + replacements[tag]['output_path'] + ',' + ','.join(options)
        result.append(line)
    if seen != set(replacements):
        raise ValueError('reviewed resource tag absent from template')
    return ('\n'.join(result) + '\n').encode()


def render_beta(meta, root=ROOT):
    base = (root / meta['foundation_profile_path']).read_bytes()
    if sha(base) != meta['foundation_profile_sha256']:
        raise ValueError('beta foundation bytes changed')
    lines = base.decode().splitlines()
    lines[0] = '# LoonKit ' + meta['version'] + ' · BETA TEST ONLY'
    routine = meta.get('upstream_overlays', {})
    at = next(i for i,x in enumerate(lines) if 'tag=Beta-AdBlock-Balanced,' in x) + 1
    lines[at:at] = [routine[g]['uri'] + ', policy=' + g + ', tag=Beta-Upstream-' + g + ', enabled=true' for g in sorted(routine)]
    profile = ('\n'.join(lines) + '\n').encode()
    updated = copy.deepcopy(meta)
    updated['configuration_sha256'] = sha(profile)
    updated['runtime_resources'] = records(profile, root)
    updated['runtime_remote_count'] = len(updated['runtime_resources'])
    foundation_raw = (root / meta['foundation_manifest_path']).read_bytes()
    if sha(foundation_raw) != meta['foundation_manifest_sha256']:
        raise ValueError('beta foundation manifest changed')
    foundation = json.loads(foundation_raw)
    tags = copy.deepcopy(foundation['source_group_tags'])
    for g in routine:
        tags[g] = ['Beta-Upstream-' + g] + tags[g]
    updated['source_group_tags'] = tags
    by_tag = {r['tag']:r for r in updated['runtime_resources']}
    updated['source_group_counts'] = {g:len(set().union(*(set(content_rules((root / by_tag[t]['path']).read_bytes())) for t in ts))) for g,ts in tags.items()}
    return profile, updated


def verify_v657(root=ROOT, remote=False):
    current_spec = read_json(root, 'build/release_spec.json')
    archived = current_spec['stable_release_version'] != 'v6.5.7'
    prefix = 'build/baselines/v6.5.7/' if archived else 'build/'
    spec = read_json(root, prefix + 'release_spec.json')
    meta = read_json(root, prefix + 'release_manifest.json')
    decision = read_json(root, spec['release_gate_file'])
    if spec['stable_release_version'] != meta['label'] or meta['label'] != 'v6.5.7':
        raise ValueError('reviewed version identity differs')
    profile = (root / ('build/baselines/v6.5.7/LoonKit.lcf' if archived else 'LoonKit.lcf')).read_bytes()
    if render(spec['reviewed_assets_commit'], root) != profile:
        raise ValueError('formal profile is not the reviewed deterministic build')
    if decision['release_profile_sha256'] != sha(profile) or decision['version'] != meta['label'] or decision['decision'] != 'OWNER_REQUESTED_AUDIT_FIXES_AND_PUBLICATION':
        raise ValueError('owner scope does not identify this exact release')
    from verify_release import check_public_checksums, check_lock, LINK
    check_public_checksums(root, read_json(root,'build/release_manifest.json'), current_spec)
    check_lock(root)
    for path, raw in render_rules(root).items():
        if (root / path).read_bytes() != raw:
            raise ValueError('reviewed resource does not rebuild: ' + path)
    baseline = read_json(root, 'build/baselines/v6.5.6/release_manifest.json')
    frozen = (root / 'build/baselines/v6.5.6/LoonKit.lcf').read_bytes()
    if section(profile.decode(),'General') != section(frozen.decode(),'General'):
        raise ValueError('General controls changed outside approved scope')
    for name in ['Proxy','Remote Proxy','Remote Filter','Proxy Group','Rule','Plugin']:
        if section(profile.decode(),name) != section(frozen.decode(),name):
            raise ValueError('non-resource section changed: ' + name)
    resources = validate_records(profile, meta['runtime_resources'], root, remote)
    if len(resources) != len(baseline['runtime_resources']) or sum(r['matcher_count'] for r in resources) != meta['remote_rule_count']:
        raise ValueError('resource manifest count differs')
    by_tag = {r['tag']:r for r in resources}
    expected_roots = {g:[rule.split(',')[1] for rule in content_rules((root / by_tag['Beta-Service-'+g]['path']).read_bytes()) if rule.startswith('DOMAIN-SUFFIX,')]
                      for g in ('Spotify','Twitch','Abema','BBC','Line','Reddit','Linkedin')}
    if meta['service_roots'] != expected_roots or meta['rules'] != baseline['rules']:
        raise ValueError('current service registry or legacy rule inventory drift')
    computed_counts = {}
    for group,tags in meta['source_group_tags'].items():
        policy = {'ChinaDirect':'DIRECT','DomesticCore':'DIRECT','SteamCN':'DIRECT','AppleOTA':'Apple'}.get(group,group)
        if any(by_tag[t]['policy'] != policy for t in tags):
            raise ValueError('source group owner drift')
        computed_counts[group] = len(set().union(*(set(content_rules((root / by_tag[t]['path']).read_bytes())) for t in tags)))
    if computed_counts != meta['source_group_counts']:
        raise ValueError('source group matcher count drift')
    # Historical validation is deliberately independent of the active beta.
    from verify_release_v656 import verify as verify_history
    verify_history(root=root, remote=remote)
    for commit,path in LINK.findall(profile.decode()):
        if not (root / path).is_file():
            raise ValueError('missing published auxiliary asset: ' + path)
    return {'release':meta['label'],'resources':len(resources),'matchers':meta['remote_rule_count'], 'sha256':sha(profile),'remote_checked':remote}


def verify(root=ROOT, remote=False):
    version = read_json(root, 'build/release_spec.json')['stable_release_version']
    if version == 'v6.5.7':
        return verify_v657(root, remote)
    if version == 'v6.5.8':
        from release_v658 import verify as verify_current
        return verify_current(root, remote)
    if version == 'v7.0.3':
        from release_v703 import check as verify_current
        result = verify_current(remote=remote,root=root)
        return {'release':result['version'],**result}
    if version == 'v7.0.0':
        from release_v700 import verify as verify_current
        return verify_current(root, remote)
    if version == 'v6.5.10':
        from release_v6510 import verify as verify_current
        return verify_current(root, remote)
    if version == 'v6.5.9':
        from release_v659 import verify as verify_current
        return verify_current(root, remote)
    raise ValueError('unsupported reviewed release version')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--check',action='store_true',required=True)
    p.add_argument('--remote',action='store_true')
    args = p.parse_args()
    print(json.dumps(verify(remote=args.remote),sort_keys=True))
