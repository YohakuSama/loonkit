"""Guard formal v6.5.9 native-only Loon release, including v6.5.8 rollback.

The full production entry replaces old AND/GEOIP service expressions with plain
DOMAIN / DOMAIN-SUFFIX, and drops the redundant remote RegionalCN. These
assertions are intentionally NOT claims about DNS leaks or live iOS stability.
"""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from release_v659 import (render as render_v659, rebuilt_service, SERVICES,
                          EXPECTED_COUNTS, PINNED_RULE_COMMIT)
from beta_channel import content_rules, remote_entries
from release_v6510 import render as render_v6510


class TestFormalNativeRelease(unittest.TestCase):
    def test_live_profile_is_exact_patch_of_frozen_v658(self):
        self.assertEqual((ROOT / "build/baselines/v6.5.9/LoonKit.lcf").read_bytes(), render_v659(ROOT))
        self.assertEqual((ROOT / "LoonKit.lcf").read_bytes(), render_v6510(ROOT))
        archived = (ROOT / "build/baselines/v6.5.8/LoonKit.lcf").read_text()
        self.assertEqual(
            sum("tag=Our-RegionalCN," in l for l in archived.splitlines()), 1)
        current = (ROOT / "LoonKit.lcf").read_text()
        self.assertNotIn("tag=Our-RegionalCN,", current)
        self.assertIn("\nGEOIP,CN,DIRECT,no-resolve\nFINAL,Final\n", current)
        self.assertEqual(len(remote_entries(current)), 36)

    def test_native_service_rules_have_no_nested_conditions(self):
        current = (ROOT / "LoonKit.lcf").read_text()
        for name in SERVICES:
            with self.subTest(name=name):
                path = ROOT / f"rules/releases/v6.5.9/{name}.list"
                self.assertEqual(path.read_bytes(), rebuilt_service(name, ROOT))
                rules = content_rules(path.read_bytes())
                self.assertEqual(len(rules), EXPECTED_COUNTS[name])
                self.assertTrue(all(x.startswith(("DOMAIN,", "DOMAIN-SUFFIX,"))
                                    for x in rules))
                self.assertFalse(any(
                    x.startswith(("AND,", "OR,", "NOT,", "GEOIP,"))
                    for x in rules))
                self.assertIn(PINNED_RULE_COMMIT + f"/rules/releases/v6.5.9/{name}.list",
                              current)

    def test_no_duplicate_cn_remote_or_retired_experimental_entry(self):
        current = (ROOT / "LoonKit.lcf").read_text()
        self.assertEqual(
            current.split("[Rule]\n",1)[1].split("\n[",1)[0]
                   .strip().splitlines()[-2:],
            ["GEOIP,CN,DIRECT,no-resolve","FINAL,Final"])
        self.assertFalse((ROOT / "LoonKit.NativeRulesTrial.lcf").exists())
        self.assertFalse(
            (ROOT / "rules/experiments/v6.5.8-native-no-composite").exists())
        meta = json.loads((ROOT / "build/release_manifest.json").read_text())
        self.assertEqual(meta["runtime_rule_count"], 36)
        self.assertEqual(meta["remote_rule_count"], 196486)
        self.assertEqual(meta["label"], "v6.5.10")
        self.assertNotIn("Our-RegionalCN",
                         {r["tag"] for r in meta["runtime_resources"]})


if __name__ == "__main__":
    unittest.main()
