#!/usr/bin/env python3
"""Pinned resource integrity and deterministic beta foundation rendering."""
from __future__ import annotations
import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen
from loon_resources import ROOT, remote_entries, content_rules, section


def sha(data):
    return hashlib.sha256(data).hexdigest()


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
