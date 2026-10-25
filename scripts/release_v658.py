"""Build and verify v6.5.8 from the frozen v6.5.7 release."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from beta_channel import ROOT, content_rules, section
from regional_rules import wrap

RECIPE = 'rules/reviewed/v6.5.8/decisions.json'


def recipe(root=ROOT):
    return json.loads((root / RECIPE).read_text())


def render_rules(root=ROOT):
    from reviewed_release import sha
    spec = recipe(root)
    output, domestic = {}, set()
    for row in spec['rules']:
        raw = (root / row['source_path']).read_bytes()
        if sha(raw) != row['source_sha256']:
            raise ValueError('v6.5.8 source hash mismatch: ' + row['tag'])
        rules = content_rules(raw)
        if len(row['remove_exact']) != len(set(row['remove_exact'])) or any(rules.count(x) != 1 for x in row['remove_exact']):
            raise ValueError('v6.5.8 exclusions changed: ' + row['tag'])
        remaining = [r for r in rules if r not in row['remove_exact']]
        if row['owner'] == 'DIRECT':
            domestic.update(wrap(r, True) for r in row['remove_exact'])
        if row['regional']:
            domestic.update(wrap(r, True) for r in remaining)
            remaining = [wrap(r, False) for r in remaining]
        output[row['output_path']] = ('# LoonKit v6.5.8 ' + row['owner'] + '\n' + '\n'.join(remaining) + '\n').encode()
    domestic.update(wrap('DOMAIN-SUFFIX,' + root, True) for root in spec['shared_cn_roots'])
    from upstream_review import _same_policy_reduce
    from regional_rules import source_matcher
    reduced,_ = _same_policy_reduce({source_matcher(r) for r in domestic})
    suffixes={r.split(',')[1] for r in reduced if r.startswith('DOMAIN-SUFFIX,')}
    reduced={r for r in reduced if not r.startswith('DOMAIN-SUFFIX,') or
             not any('.'.join(r.split(',')[1].split('.')[i:]) in suffixes
                     for i in range(1,len(r.split(',')[1].split('.'))))}
    domestic={wrap(r,True) for r in reduced}
    output[spec['regional_cn_path']] = ('# LoonKit v6.5.8 Regional CN\n' + '\n'.join(sorted(domestic)) + '\n').encode()
    return output


def render(asset_commit, root=ROOT):
    from reviewed_release import sha
    if not re.fullmatch('[a-f0-9]{40}', asset_commit):
        raise ValueError('immutable asset commit required')
    spec = recipe(root)
    base = (root / spec['base_profile_path']).read_bytes()
    if sha(base) != spec['base_profile_sha256']:
        raise ValueError('v6.5.7 template hash mismatch')
    replacements = {r['tag']:r for r in spec['rules']}
    output, seen = ['# LoonKit v6.5.8'], set()
    raw = 'https://raw.githubusercontent.com/YohakuSama/loonkit/' + asset_commit + '/'
    for line in base.decode().splitlines()[1:]:
        if line.lstrip().startswith('#'):
            continue
        if line == '[Rule]':
            output.extend(['[Host]',spec['dns_bootstrap_host'] + ' = ' + spec['dns_bootstrap_ip'],''])
        if line.startswith('doh-server = '):
            line = 'doh-server = ' + ','.join(spec['doh_servers'])
        if any(line.startswith(g + ' = ') for g in spec['regional_owners']):
            line = line.replace('select,DIRECT,Proxy,Auto,Fallback,ALL_Filter,', 'select,Proxy,Auto,Fallback,ALL_Filter,', 1)
        if line.startswith('https://') and ', policy=' in line:
            uri, *options = line.split(',')
            flags = dict(x.strip().split('=',1) for x in options)
            if flags['tag'] in replacements:
                seen.add(flags['tag'])
                line = raw + replacements[flags['tag']]['output_path'] + ',' + ','.join(options)
        output.append(line)
        if 'tag=Beta-AdBlock-Balanced,' in line:
            output.append(raw + spec['regional_cn_path'] + ', policy=DIRECT, tag=Our-RegionalCN, enabled=true')
    if seen != set(replacements):
        raise ValueError('missing reviewed resource tags')
    return (re.sub(r'\n{3,}','\n\n','\n'.join(output)).rstrip() + '\n').encode()


def directives(text):
    return [x for x in text.splitlines() if x.strip() and not x.lstrip().startswith('#')]


def verify(root=ROOT, remote=False):
    from reviewed_release import sha, validate_records, verify_v657
    from verify_release import check_public_checksums, check_lock
    spec = json.loads((root / 'build/release_spec.json').read_text())
    meta = json.loads((root / 'build/release_manifest.json').read_text())
    profile = (root / 'LoonKit.lcf').read_bytes()
    decision = json.loads((root / spec['release_gate_file']).read_text())
    if spec['stable_release_version'] != 'v6.5.8' or meta['label'] != 'v6.5.8':
        raise ValueError('v6.5.8 version identity mismatch')
    if render(spec['reviewed_assets_commit'], root) != profile:
        raise ValueError('v6.5.8 profile differs from deterministic build')
    if decision['version'] != meta['label'] or decision['release_profile_sha256'] != sha(profile) or decision['decision'] != 'OWNER_REQUESTED_AUDIT_FIXES_AND_PUBLICATION':
        raise ValueError('release decision hash mismatch')
    check_public_checksums(root, meta, spec)
    check_lock(root)
    for path, raw in render_rules(root).items():
        if (root / path).read_bytes() != raw:
            raise ValueError('v6.5.8 resource differs from build: ' + path)
    resources = validate_records(profile, meta['runtime_resources'], root, remote)
    if len(resources) != 37 or len(resources) != meta['runtime_rule_count'] or sum(r['matcher_count'] for r in resources) != meta['remote_rule_count']:
        raise ValueError('v6.5.8 resource inventory mismatch')
    rules = [r for row in resources for r in content_rules((root / row['path']).read_bytes())]
    if any(r.startswith(('USER-AGENT,','DOMAIN-KEYWORD,')) for r in rules):
        raise ValueError('broad UA/keyword rules reintroduced')
    baseline = (root / recipe(root)['base_profile_path']).read_text()
    text = profile.decode()
    for name in ('Proxy','Remote Proxy','Remote Filter','Rule','Plugin'):
        if directives(section(text,name)) != directives(section(baseline,name)):
            raise ValueError('protected section changed: ' + name)
    before = directives(section(baseline,'General'))
    after = directives(section(text,'General'))
    before = [r for r in before if not r.startswith('doh-server = ')]
    after = [r for r in after if not r.startswith('doh-server = ')]
    if before != after or 'GEOIP,CN,DIRECT,no-resolve' not in directives(section(text,'Rule')):
        raise ValueError('protected network controls changed')
    if directives(section(text,'Host')) != ['dns.alidns.com = 223.5.5.5']:
        raise ValueError('DNS bootstrap mapping changed')
    expected_groups = section(baseline,'Proxy Group')
    for group in recipe(root)['regional_owners']:
        expected_groups = re.sub(r'(?m)^' + re.escape(group) + r' = select,DIRECT,Proxy,Auto,Fallback,ALL_Filter,', group + ' = select,Proxy,Auto,Fallback,ALL_Filter,', expected_groups)
    if directives(expected_groups) != directives(section(text,'Proxy Group')):
        raise ValueError('unreviewed policy defaults changed')
    by_tag = {r['tag']:r for r in resources}
    previous=json.loads((root/'build/baselines/v6.5.7/release_manifest.json').read_text())
    expected_roots={g:[r.split(',')[1] for r in content_rules((root/by_tag['Beta-Service-'+g]['path']).read_bytes()) if r.startswith('DOMAIN-SUFFIX,')]
                    for g in ('Spotify','Twitch','Abema','BBC','Line','Reddit','Linkedin')}
    if (meta['source_group_tags'] != previous['source_group_tags'] or meta['rules'] != previous['rules']
            or meta['service_roots'] != expected_roots or meta['reviewed_recipe'] != RECIPE
            or meta['reviewed_assets_commit'] != spec['reviewed_assets_commit']):
        raise ValueError('current source inventory or release references drifted')
    beta=json.loads((root/'build/beta_manifest.json').read_text())
    if beta['stable_release'] != meta['label'] or beta['foundation_profile_sha256'] != sha(profile):
        raise ValueError('beta stable foundation identity drifted')
    if '**v6.5.8**' not in (root/'README.md').read_text():
        raise ValueError('README version differs from current release')
    for group,tags in meta['source_group_tags'].items():
        count = len(set().union(*(set(content_rules((root / by_tag[t]['path']).read_bytes())) for t in tags)))
        policy = {'ChinaDirect':'DIRECT','DomesticCore':'DIRECT','SteamCN':'DIRECT','AppleOTA':'Apple'}.get(group,group)
        if count != meta['source_group_counts'][group] or any(by_tag[t]['policy'] != policy for t in tags):
            raise ValueError('source baseline ownership/count changed: ' + group)
    historical = verify_v657(root, remote)
    return {'release':'v6.5.8','resources':len(resources),'matchers':len(rules),'sha256':sha(profile),'remote_checked':remote,'previous_release':historical['release']}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--check',action='store_true',required=True)
    p.add_argument('--remote',action='store_true')
    args = p.parse_args()
    print(json.dumps(verify(remote=args.remote),sort_keys=True))
