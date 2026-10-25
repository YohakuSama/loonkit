"""Exact beta promotion remains reproducible and tampering is rejected."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import prepare_promoted_release as build
import prepare_release_v656 as new_build
import verify_promoted as release
import beta_channel


class PublishedCandidateTests(unittest.TestCase):
    def test_deterministic_migration_matches_formal_config(self):
        expected = (ROOT/"build/baselines/v6.5.5/LoonKit.lcf").read_bytes()
        self.assertEqual(build.render(), expected)
        self.assertEqual(build.check()["sha256"], hashlib.sha256(expected).hexdigest())
        self.assertEqual(release.active(expected), release.active((ROOT/"build/baselines/v6.5.5-beta.4/LoonKit.lcf").read_bytes()))
        self.assertEqual(new_build.render(), (ROOT/"build/baselines/v6.5.6/LoonKit.lcf").read_bytes())
        self.assertTrue(all(ord(c) < 128 for line in expected.decode().splitlines()
                            if line.lstrip().startswith("#") for c in line))

    def test_exact_immutable_record_and_service_ownership(self):
        published=json.loads((ROOT/"build/baselines/v6.5.5/release_manifest.json").read_text())
        original=json.loads((ROOT/"build/baselines/v6.5.5-beta.4/beta_manifest.json").read_text())
        self.assertEqual(published["promoted_beta_config_sha256"], original["configuration_sha256"])
        self.assertEqual(published["promoted_beta_commit_sha"], release.CANDIDATE_COMMIT)
        self.assertEqual(published["promoted_beta_asset_commit"], release.ASSET_COMMIT)
        items=beta_channel.remote_entries((ROOT/"build/baselines/v6.5.5/LoonKit.lcf").read_text())
        self.assertEqual(len(items), 36)
        self.assertEqual([(r["uri"],r["policy"],r["tag"]) for r in items],
                         [(r["uri"],r["policy"],r["tag"]) for r in
                          published["runtime_resources"]])
        self.assertEqual([i["tag"] for i in items if i["policy"]=="AdBlock"],
                         ["Beta-AdBlock-Balanced"])
        self.assertEqual(published["runtime_rule_matcher_count"],
                         sum(x["matcher_count"] for x in published["runtime_resources"]))

    def test_modified_directive_fails_exact_comparison(self):
        source=(ROOT/"build/baselines/v6.5.5/LoonKit.lcf").read_bytes()
        candidate=(ROOT/"build/baselines/v6.5.5-beta.4/LoonKit.lcf").read_bytes()
        changed=source.replace(b"doh-server = https://dns.alidns.com/dns-query",
                               b"doh-server = https://different.invalid/dns-query")
        self.assertNotEqual(release.active(changed), release.active(source))
        self.assertNotEqual(hashlib.sha256(changed).hexdigest(),
                            json.loads((ROOT/"build/release_manifest.json").read_text())
                            ["profile_sha256"]["LoonKit.lcf"])

    def test_one_reject_setting_change_only(self):
        old=(ROOT/"build/baselines/v6.5.5/LoonKit.lcf").read_bytes()
        new=(ROOT/"build/baselines/v6.5.6/LoonKit.lcf").read_bytes()
        expected=old.replace(b"# LoonKit v6.5.5\n",b"# LoonKit v6.5.6\n",1).replace(b"\ndns-reject-mode = NOANSWER\n",b"\ndns-reject-mode = LOOPBACKIP\n",1)
        self.assertEqual(new,expected)
        self.assertNotIn(b"[Mitm]",new)

    def test_old_template_is_not_new_formal_entry(self):
        frozen=(ROOT/"build/baselines/v6.5.4/LoonKit.lcf").read_bytes()
        manifest=json.loads((ROOT/"build/beta_manifest.json").read_text())
        self.assertEqual(hashlib.sha256(frozen).hexdigest(),
                         manifest["original_production_config_sha256"])
        self.assertNotEqual(frozen, (ROOT/"LoonKit.lcf").read_bytes())
        self.assertEqual(beta_channel.validate(profile_path="build/baselines/v6.5.5-beta.4/LoonKit.lcf", manifest_path="build/baselines/v6.5.5-beta.4/beta_manifest.json")["configuration_sha256"],
                         release.CANDIDATE_SHA)


if __name__=="__main__":
    unittest.main()
