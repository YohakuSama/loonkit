"""Independent REST-transaction tests; synthetic domains never become live rules."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import beta_upstream_delivery as delivery
from beta_github import GitHub


class FakeGitHub:
    def __init__(self, profile, meta, catalog):
        self.base = "a" * 40
        self.files = {"beta/LoonKit.lcf":profile, "build/beta_manifest.json":delivery.encoded(meta),
                      "rules/sources.json":delivery.encoded(catalog), "docs/BETA_ACCEPTANCE_TEMPLATE.json":delivery.encoded({
                          "status":"TEMPLATE_NOT_EVIDENCE", "maintainer_approved":False})}
        self.writes = []
        self.refs = {}
        self.existing_pr = []

    def file(self, path, ref):
        return self.files[path]

    def get(self, path):
        if path == "/git/ref/heads/beta":
            return {"object":{"sha":self.base}}
        if path.startswith("/git/ref/heads/"):
            return self.refs.get(path)
        if path.startswith("/pulls?"):
            return self.existing_pr
        if path.startswith("/git/commits/"):
            return {"tree":{"sha":"b"*40}}
        raise AssertionError("unexpected GET " + path)

    def post(self, path, payload):
        self.writes.append((path, copy.deepcopy(payload)))
        if path == "/pulls":
            return {"html_url":"https://github.com/YohakuSama/loonkit/pull/999"}
        if path == "/git/refs":
            self.refs["/git/ref/heads/" + payload["ref"].removeprefix("refs/heads/")] = {"object":{"sha":payload["sha"]}}
        return {"sha":hashlib.sha1(delivery.encoded(payload)).hexdigest()}


class BetaUpstreamDeliveryTests(unittest.TestCase):
    def fixture(self):
        profile = ("# LoonKit v1.2.3-beta.1 · BETA TEST ONLY\n[General]\n"
                   "dns-server = 223.5.5.5,223.6.6.6\ndoh-server = https://dns.alidns.com/dns-query\n"
                   "[Remote Rule]\nhttps://raw.githubusercontent.com/YohakuSama/loonkit/" + "b"*40 +
                   "/rules/beta/filter.list, policy=AdBlock, tag=Beta-AdBlock-Balanced, enabled=true\n"
                   "[Rule]\nGEOIP,CN,DIRECT,no-resolve\nFINAL,Final\n").encode()
        source = {"id":"video-source", "group":"YouTube", "url":"https://raw.githubusercontent.com/owner/repo/main/video.list",
                  "sha256":"c"*64, "status":"PARSED_FOR_REVIEW"}
        catalog = {"sources":[{"id":source["id"], "group":"YouTube", "url":source["url"]}]}
        meta = {"version":"v1.2.3-beta.1", "configuration_sha256":delivery.digest(profile), "upstream_overlays":{},
                "acceptance":{"promotion":"BLOCKED"}, "source_group_counts":{"YouTube":1000}}
        rule = "DOMAIN,video-reviewed-example.test"
        plan = {"schema_version":1, "repository":delivery.REPOSITORY, "base_commit":"a"*40,
                "version":"v1.2.3-beta.2", "base_configuration_sha256":delivery.digest(profile),
                "runtime_baseline":True, "source_integrity_complete":True, "source_count":1, "sources":[source],
                "groups":{"YouTube":{"rules":[rule], "provenance":{rule:[source["id"]]}}},
                "full_diff_sha256":"d"*64, "created_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")}
        return plan, FakeGitHub(profile, meta, catalog)

    def test_two_commits_pin_assets_before_importable_profile_and_dispatch_exact_ci(self):
        plan, api = self.fixture()
        out = delivery.publish(plan, api)
        commits = [x for path,x in api.writes if path == "/git/commits"]
        trees = [x for path,x in api.writes if path == "/git/trees"]
        self.assertEqual(len(commits), 2)
        self.assertEqual(commits[0]["parents"], [plan["base_commit"]])
        self.assertEqual(commits[1]["parents"], [out["asset_commit"]])
        self.assertEqual({x["path"] for x in trees[0]["tree"]}, {"rules/beta/upstream/v1.2.3-beta.2/YouTube.list"})
        updated = {x["path"]:x["content"] for x in trees[1]["tree"]}
        self.assertNotIn("LoonKit.lcf", updated)
        self.assertIn(out["asset_commit"], updated["beta/LoonKit.lcf"])
        old_dns = api.files["beta/LoonKit.lcf"].decode().split("[General]\n")[1].split("[Remote Rule]")[0]
        new_dns = updated["beta/LoonKit.lcf"].split("[General]\n")[1].split("[Remote Rule]")[0]
        self.assertEqual(old_dns, new_dns)
        self.assertEqual(json.loads(updated["build/beta_manifest.json"])["acceptance"]["promotion"], "BLOCKED")
        self.assertTrue(next(p for path,p in api.writes if path == "/pulls")["draft"])
        self.assertEqual(api.writes[-1], ("/actions/workflows/beta-ci.yml/dispatches", {"ref":out["branch"]}))

    def test_bad_or_sensitive_delta_never_creates_commits_refs_or_pr(self):
        for bad in ("direct", "suffix", "shared", "source", "duplicate", "version", "hash", "future", "missing_provenance"):
            with self.subTest(bad=bad):
                plan, api = self.fixture()
                selection = plan["groups"]["YouTube"]
                if bad == "direct": plan["groups"] = {"ChinaDirect":selection}
                if bad in {"suffix", "shared"}:
                    rule = "DOMAIN-SUFFIX,example.test" if bad == "suffix" else "DOMAIN,tenant.cloudfront.net"
                    selection["rules"] = [rule]; selection["provenance"] = {rule:["video-source"]}
                if bad == "source": plan["source_integrity_complete"] = False
                if bad == "duplicate": selection["rules"] *= 2
                if bad == "version": plan["version"] = "v1.2.3-beta.99"
                if bad == "hash": plan["base_configuration_sha256"] = "0"*64
                if bad == "future": plan["created_at_utc"] = "2099-01-01T00:00:00Z"
                if bad == "missing_provenance": selection["provenance"] = {}
                with self.assertRaises(ValueError): delivery.publish(plan, api)
                self.assertEqual(api.writes, [])

    def test_stale_beta_noop_and_repeated_plan_are_safe(self):
        plan, api = self.fixture(); api.base = "f"*40
        with self.assertRaisesRegex(ValueError, "moved"): delivery.publish(plan, api)
        self.assertEqual(api.writes, [])
        plan, api = self.fixture(); plan["groups"] = {}
        self.assertEqual(delivery.publish(plan, api)["status"], "NO_ELIGIBLE_RUNTIME_CHANGE")
        self.assertEqual(api.writes, [])
        plan, api = self.fixture(); first = delivery.publish(plan, api)
        api.existing_pr = [{"html_url":first["pull_request"]}]
        writes = len(api.writes)
        self.assertEqual(delivery.publish(plan, api)["status"], "EXISTING_PR_UNMODIFIED")
        self.assertEqual(len(api.writes), writes)

    def test_existing_runtime_overlay_is_retained_and_hash_checked(self):
        plan, api = self.fixture()
        meta = json.loads(api.files["build/beta_manifest.json"])
        raw = b"# prior reviewed additions\nDOMAIN,prior-video.test\n"
        path = "rules/beta/upstream/v1.2.3-beta.1/YouTube.list"
        meta["upstream_overlays"]["YouTube"] = {"uri":delivery.RAW + "e"*40 + "/" + path, "sha256":delivery.digest(raw)}
        api.files["build/beta_manifest.json"] = delivery.encoded(meta); api.files[path] = raw
        delivery.publish(plan, api)
        tree = next(data for path,data in api.writes if path == "/git/trees")
        self.assertIn("DOMAIN,prior-video.test", tree["tree"][0]["content"])
        self.assertIn("DOMAIN,video-reviewed-example.test", tree["tree"][0]["content"])

    def test_trusted_publisher_rejects_existing_and_regional_owners(self):
        for host in ('www.microsoft.com','servicewechat.com'):
            plan,api=self.fixture()
            rule='DOMAIN,'+host
            plan['groups']['YouTube']={'rules':[rule],'provenance':{rule:['video-source']}}
            with self.assertRaisesRegex(ValueError,'already covered'):
                delivery.publish(plan,api)
            self.assertEqual(api.writes,[])

    def test_github_client_handles_dispatch_204_without_json_or_token_logging(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): return b""
        client = GitHub("synthetic-not-a-token")
        with patch.object(client._opener, "open", return_value=Response()):
            self.assertIsNone(client.post("/actions/workflows/beta-ci.yml/dispatches", {"ref":"synthetic"}))


if __name__ == "__main__":
    unittest.main()
