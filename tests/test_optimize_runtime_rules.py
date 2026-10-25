"""Lossless Loon rule subset elimination must preserve first-match ownership."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from optimize_runtime_rules import trim_rules


class OptimizationTests(unittest.TestCase):
    def test_exact_domain_and_suffix_are_safe_same_subscription(self):
        raw = (b"# preserved header\n"
               b"DOMAIN,api.example.org\nDOMAIN-SUFFIX,example.org\n"
               b"DOMAIN-SUFFIX,child.example.org\nDOMAIN,another.example.org\n")
        result, report, removed = trim_rules(raw)
        self.assertEqual(report["removed"], 3)
        self.assertEqual(result, b"# preserved header\nDOMAIN-SUFFIX,example.org\n")
        self.assertEqual(len(removed), 3)

    def test_do_not_merge_across_different_ip_flags(self):
        raw = (b"IP-CIDR,198.18.0.0/15,no-resolve\n"
               b"IP-CIDR,198.18.1.0/24\n"
               b"IP-CIDR,198.18.1.128/25,no-resolve\n"
               b"IP-CIDR6,2001:db8::/32,no-resolve\n"
               b"IP-CIDR6,2001:db8:1234::/48,no-resolve\n")
        result, stats, _ = trim_rules(raw)
        self.assertEqual(stats["removed"], 2)
        self.assertIn(b"IP-CIDR,198.18.1.0/24\n", result)
        self.assertNotIn(b"IP-CIDR6,2001:db8:1234::/48", result)

    def test_keyword_and_unrelated_suffix_are_unchanged(self):
        raw = b"DOMAIN-KEYWORD,example\nDOMAIN,api.example.org\nDOMAIN-SUFFIX,another.org\n"
        result, meta, _ = trim_rules(raw)
        self.assertEqual(result, raw)
        self.assertEqual(meta["removed"], 0)

    def test_same_rule_duplicate_is_removed(self):
        data = b"DOMAIN-SUFFIX,example.org\nDOMAIN-SUFFIX,example.org\n"
        result, meta, _ = trim_rules(data)
        self.assertEqual(result, b"DOMAIN-SUFFIX,example.org\n")
        self.assertEqual(meta["reasons"]["EXACT_DUPLICATE"], 1)

    def test_full_inventory_is_readonly_and_manifest_consistent(self):
        import json
        from optimize_runtime_rules import audit
        report = audit()
        manifest = json.loads((ROOT / "build/release_manifest.json").read_text())
        self.assertEqual(report["totals"]["before"], manifest["runtime_rule_matcher_count"])
        self.assertEqual(report["sources"], len(manifest["runtime_resources"]))


if __name__ == "__main__":
    unittest.main()
