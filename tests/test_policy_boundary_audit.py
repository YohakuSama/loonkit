"""Regression tests for effective remote-rule boundaries and Final fallback."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from policy_boundary_audit import analyze


class PolicyBoundaryAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = analyze()
        cls.tags = [
            row["tag"] for row in
            json.loads((ROOT / "build/profile.json").read_text(encoding="utf-8"))["remote_rules"]
        ]
        cls.candidates = {
            "Our-Apple": "rules/releases/v7.0.16/Apple.lsr",
            "Our-SharedInfrastructure": "rules/releases/v7.0.16/SharedInfrastructure.lsr",
        }

    def test_active_remote_assets_match_manifest_and_final(self):
        manifest = json.loads((ROOT / "build/release_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(self.base["remote_subscriptions"], manifest["remote_subscription_count"])
        self.assertEqual(self.base["remote_rules"], manifest["remote_rule_count"])
        self.assertEqual(self.base["final_rule"], "FINAL,Final")
        self.assertTrue(self.base["geoip_cn_before_final"])

    def test_apple_private_cloud_compute_requires_explicit_priority(self):
        original = analyze(replacements=self.candidates)
        prior = [
            p for p in original["policy_pairs"]
            if p["earlier_policy"] == "Cloudflare" and p["later_policy"] == "Apple"
        ]
        self.assertGreaterEqual(sum(p["count"] for p in prior), 2)
        order = list(self.tags)
        # Keep the original AppleOTA-before-Apple order, then put both before
        # the generic Cloudflare domain suffix. They retain policy=Apple.
        order.remove("Our-Apple")
        order.remove("Our-AppleOTA")
        slot = order.index("Our-Cloudflare")
        order[slot:slot] = ["Our-AppleOTA", "Our-Apple"]
        checks = (
            "apple-relay.cloudflare.com", "apple-relay.fastly-edge.com",
            "cp4.cloudflare.com", "api.cloudflare.com", "guzzoni.apple.com",
            "search.smoot.apple.com", "api.stripe.com", "m.stripe.network",
            "stripe.com", "google.com", "youtube.com", "chatgpt.com",
            "raw.githubusercontent.com", "quark.cn", "example-unknown.invalid",
        )
        fixed = analyze(replacements=self.candidates, priority=tuple(order), probes=checks)
        expected = {
            "apple-relay.cloudflare.com": "Apple",
            "apple-relay.fastly-edge.com": "Apple",
            "cp4.cloudflare.com": "Apple",
            "api.cloudflare.com": "Cloudflare",
            "guzzoni.apple.com": "Apple",
            "search.smoot.apple.com": "Apple",
            "api.stripe.com": "Proxy",
            "m.stripe.network": "Proxy",
            "stripe.com": "Proxy",
            "google.com": "Google",
            "youtube.com": "YouTube",
            "chatgpt.com": "ChatGPT",
            "raw.githubusercontent.com": "Proxy",
            "quark.cn": "DIRECT",
            "example-unknown.invalid": "Final (subject to GEOIP/ASN/runtime)",
        }
        for host, policy in expected.items():
            with self.subTest(host=host):
                self.assertEqual(fixed["domain_probes"][host]["policy"], policy)
        # A new rule must not unexpectedly hide a rule of another service.
        baseline = {
            (x["earlier_policy"], x["later_policy"], x["reason"]): x["count"]
            for x in self.base["policy_pairs"] if x["reason"] != "LATER_BROAD_SUFFIX_OVERLAP"
        }
        proposed = {
            (x["earlier_policy"], x["later_policy"], x["reason"]): x["count"]
            for x in fixed["policy_pairs"] if x["reason"] != "LATER_BROAD_SUFFIX_OVERLAP"
        }
        for key, count in proposed.items():
            self.assertLessEqual(count, baseline.get(key, 0), "new full shadow: " + str(key))
        print("POLICY_AUDIT_CANDIDATE_PROBES", json.dumps(fixed["domain_probes"], ensure_ascii=False))
        shadowed = [
            p for p in fixed["policy_pairs"]
            if p["earlier_policy"] == "Cloudflare" and p["later_policy"] == "Apple"
        ]
        self.assertEqual(sum(p["count"] for p in shadowed), 0)
        print("POLICY_AUDIT_BASELINE", json.dumps({
            "counts": self.base["summary"],
            "top_pairs": self.base["policy_pairs"][:25],
        }, ensure_ascii=False))
        from route_diagnostics import Router
        router = Router()
        sample = (
            "apple.com", "guzzoni.apple.com", "search.smoot.apple.com",
            "apple-relay.cloudflare.com", "cp4.cloudflare.com",
            "apple-relay.fastly-edge.com", "api.cloudflare.com",
            "google.com", "beacons.gvt2.com", "youtube.com",
            "github.com", "raw.githubusercontent.com", "copilot.microsoft.com",
            "openai.com", "chatgpt.com", "anthropic.com", "gemini.google.com",
            "microsoft.com", "wikipedia.org", "reddit.com", "discord.com",
            "telegram.org", "netflix.com", "paypal.com", "steamcommunity.com",
            "quark.cn", "stripe.com", "api.stripe.com", "m.stripe.network", "cloudflare.com",
            "never-registered-service-example.invalid",
        )
        print("POLICY_AUDIT_ROUTE_PROBES", json.dumps({
            host: router.match(host)["predicted_policy"] for host in sample
        }, ensure_ascii=False))
        print("POLICY_AUDIT_APPLE_PREVIEW", json.dumps({
            "counts": fixed["summary"],
            "top_pairs": fixed["policy_pairs"][:25],
        }, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
