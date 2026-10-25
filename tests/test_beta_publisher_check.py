"""Publisher check exercises real API operations without changing runtime files."""
import copy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from beta_publisher_check import check
from beta_github import GitHub


class API:
    def __init__(self,fail_pr=False,conclusion='success',move=False):
        self.calls=[];self.ref=None;self.fail_pr=fail_pr;self.conclusion=conclusion;self.move=move
    def file(self,path,ref):return b'# LoonKit check profile\n'
    def get(self,path):
        if path=='/git/ref/heads/beta':return {'object':{'sha':'a'*40}}
        if path.startswith('/git/ref/heads/automation/'):
            return {'object':{'sha':('d'*40 if self.move else self.ref)}} if self.ref else None
        if path.startswith('/git/commits/'):return {'tree':{'sha':'b'*40}}
        if path.startswith('/actions/workflows/'):
            return {'workflow_runs':[{'id':8,'head_sha':'c'*40,'head_branch':'automation/publisher-check-123-1','event':'workflow_dispatch','status':'completed','conclusion':self.conclusion,'html_url':'https://github.com/YohakuSama/loonkit/actions/runs/8'}]}
        raise AssertionError(path)
    def post(self,path,body):
        self.calls.append((path,copy.deepcopy(body)))
        if path=='/git/refs':self.ref=body['sha']
        if path=='/pulls':
            if self.fail_pr:raise RuntimeError('HTTP 403')
            return {'number':123,'html_url':'https://github.com/YohakuSama/loonkit/pull/123'}
        return {'sha':'c'*40}
    def close_check_pr(self,number):self.calls.append(('close',number))
    def delete_check_branch(self,branch):self.calls.append(('delete',branch));self.ref=None


class PublisherCheckTests(unittest.TestCase):
    def test_exact_ci_dispatch_and_cleanup_with_no_runtime_change(self):
        api=API();result=check(api,'123','1',sleep=lambda _:None)
        self.assertEqual(result['status'],'REAL_PR_AND_EXACT_HEAD_CI_VERIFIED')
        self.assertTrue(result['check_pr_closed']);self.assertTrue(result['check_branch_removed'])
        tree=next(body for path,body in api.calls if path=='/git/trees')
        self.assertEqual([row['path'] for row in tree['tree']],['docs/automation/publisher-check.json'])
        self.assertIn(('/actions/workflows/beta-ci.yml/dispatches',{'ref':'automation/publisher-check-123-1'}),api.calls)
        self.assertIsNone(api.ref)

    def test_pr_permission_failure_removes_only_the_temporary_branch(self):
        api=API(fail_pr=True)
        with self.assertRaisesRegex(RuntimeError,'403'):check(api,'123','1',sleep=lambda _:None)
        self.assertIsNone(api.ref)
        self.assertFalse(any(path=='close' for path,_ in api.calls))

    def test_failed_ci_closes_pr_and_removes_branch(self):
        api=API(conclusion='failure')
        with self.assertRaisesRegex(ValueError,'CI failed'):check(api,'123','1',sleep=lambda _:None)
        self.assertIsNone(api.ref)
        self.assertIn(('close',123),api.calls)

    def test_moved_check_branch_is_retained(self):
        api=API(move=True)
        with self.assertRaisesRegex(ValueError,'branch moved'):check(api,'123','1',sleep=lambda _:None)
        self.assertFalse(any(path=='delete' for path,_ in api.calls))

    def test_cleanup_client_rejects_main_and_arbitrary_refs(self):
        api=GitHub('synthetic-token')
        for branch in ('main','beta','automation/publisher-check-human'):
            with self.assertRaises(ValueError):api.delete_check_branch(branch)
        with self.assertRaises(ValueError):api.request('DELETE','/git/refs/heads/main')


if __name__=='__main__':unittest.main()
