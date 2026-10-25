"""Verify real Actions draft-PR and exact-head CI permissions, then clean up."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time
from beta_github import GitHub


def check(client, run_id: str, attempt: str, *, sleep=time.sleep, polls=90):
    if not re.fullmatch('[0-9]+',run_id) or not re.fullmatch('[0-9]+',attempt):
        raise ValueError('numeric Actions run and attempt required')
    branch = 'automation/publisher-check-' + run_id + '-' + attempt
    if client.get('/git/ref/heads/' + branch):
        raise ValueError('check branch already exists; inspect without overwriting')
    base = client.get('/git/ref/heads/beta')['object']['sha']
    profile = client.file('beta/LoonKit.lcf',base)
    result = {'base_sha':base,'configuration_sha256':hashlib.sha256(profile).hexdigest(),'branch':branch}
    commit = client.get('/git/commits/' + base)
    tree = client.post('/git/trees',{'base_tree':commit['tree']['sha'],'tree':[
        {'path':'docs/automation/publisher-check.json','mode':'100644','type':'blob',
         'content':json.dumps({'run_id':run_id,**result},indent=2)+'\n'}]})['sha']
    head = client.post('/git/commits',{'tree':tree,'parents':[base],
        'message':'ci: verify beta publisher permissions and explicit CI dispatch'})['sha']
    client.post('/git/refs',{'ref':'refs/heads/' + branch,'sha':head})
    pr = None
    try:
        pr = client.post('/pulls',{'base':'beta','head':branch,'draft':True,
            'title':'ci: beta publisher integration check',
            'body':'Checks Actions draft-PR permissions and exact-head CI dispatch. This temporary branch changes only the check record; runtime files are identical to beta.'})
        result.update(pull_request=pr['html_url'],head_sha=head)
        client.post('/actions/workflows/beta-ci.yml/dispatches',{'ref':branch})
        for _ in range(polls):
            data = client.get('/actions/workflows/beta-ci.yml/runs?event=workflow_dispatch&head_sha=' + head + '&per_page=10') or {}
            runs = [r for r in data.get('workflow_runs',[]) if r.get('head_sha') == head and r.get('head_branch') == branch and r.get('event') == 'workflow_dispatch']
            completed = [r for r in runs if r.get('status') == 'completed']
            if completed:
                run = max(completed,key=lambda r:r['id'])
                result.update(ci_run_url=run['html_url'],ci_conclusion=run['conclusion'])
                if run['conclusion'] != 'success':
                    raise ValueError('publisher check CI failed: ' + run['html_url'])
                result['status'] = 'REAL_PR_AND_EXACT_HEAD_CI_VERIFIED'
                break
            sleep(8)
        else:
            raise TimeoutError('publisher check CI did not finish within the polling window')
    finally:
        try:
            if pr:
                client.close_check_pr(pr['number'])
                result['check_pr_closed'] = True
        finally:
            ref = client.get('/git/ref/heads/' + branch)
            if ref and ref['object']['sha'] == head:
                client.delete_check_branch(branch)
                result['check_branch_removed'] = True
            elif ref:
                raise ValueError('check branch moved; cleanup retained it')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    try:
        result = check(GitHub(os.environ.get('GITHUB_TOKEN','')),os.environ['GITHUB_RUN_ID'],os.environ['GITHUB_RUN_ATTEMPT'])
    except Exception as error:
        args.output.write_text(json.dumps({'status':'FAILED','error':str(error)},indent=2)+'\n')
        raise
    else:
        args.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,sort_keys=True))
