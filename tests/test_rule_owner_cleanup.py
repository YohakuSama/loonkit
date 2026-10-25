"""Current rule ownership after removal of redundant service matchers."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from loon_resources import content_rules
from route_diagnostics import Router


class RuleOwnerCleanupTests(unittest.TestCase):
    def test_removed_matchers_do_not_return_to_the_wrong_resource(self):
        rows = json.loads((ROOT / "build/release_manifest.json").read_text())["runtime_resources"]
        removed = {
            "Our-Netflix": ["DOMAIN-SUFFIX,fast.com"],
            "Our-TikTok": ["DOMAIN-SUFFIX,trae.ai"],
            "Our-ChinaDirect-Scoped": ["DOMAIN-SUFFIX,minimax.io", "DOMAIN-SUFFIX,z.ai"],
        }
        by_tag = {row["tag"]: row for row in rows}
        for tag, matchers in removed.items():
            rules = content_rules((ROOT / by_tag[tag]["path"]).read_bytes())
            for matcher in matchers:
                self.assertNotIn(matcher, rules, tag)

    def test_current_owner_priorities(self):
        router = Router()
        for host, policy in (("fast.com", "Speedtest"), ("trae.ai", "AI"),
                             ("minimax.io", "AI"), ("z.ai", "AI")):
            with self.subTest(host=host):
                self.assertEqual(router.match(host)["predicted_policy"], policy)


if __name__ == "__main__":
    unittest.main()
