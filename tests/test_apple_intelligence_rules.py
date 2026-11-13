"""Reviewable Apple Intelligence / Siri remote-rule additions (not a profile change)."""
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / "rules/releases/v7.0.3/Apple.lsr"
CANDIDATE = ROOT / "rules/releases/v7.0.16/Apple.lsr"

PCC_SHARED_HOSTS = (
    "apple-relay.cloudflare.com",
    "apple-relay.fastly-edge.com",
    "cp4.cloudflare.com",
)
SIRI_APPLE_HOSTS = (
    "guzzoni.apple.com",
    "search.smoot.apple.com",
    "apple-relay.apple.com",
)

SUPERSEDED_EDGEKEY_RULES = (
    "DOMAIN,lookup-api.apple.com.edgekey.net",
    "DOMAIN-SUFFIX,gsp4-cn.ls.apple.com.edgekey.net",
    "DOMAIN-SUFFIX,store.apple.com.edgekey.net",
    "DOMAIN-SUFFIX,www.apple.com.edgekey.net",
)


def rules(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def matches(rule: str, host: str) -> bool:
    parts = rule.split(",")
    if len(parts) != 2:
        return False
    kind, value = parts
    return (kind == "DOMAIN" and host == value) or (
        kind == "DOMAIN-SUFFIX" and (host == value or host.endswith("." + value))
    )


class AppleIntelligenceRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before = rules(PREVIOUS)
        cls.after = rules(CANDIDATE)

    def test_existing_apple_rules_remain_covered_and_in_order(self) -> None:
        new_iter = iter(self.after)
        retained = [rule for rule in self.before if rule not in SUPERSEDED_EDGEKEY_RULES]
        self.assertTrue(all(any(item == prior for item in new_iter) for prior in retained))
        for rule in SUPERSEDED_EDGEKEY_RULES:
            with self.subTest(superfluous=rule):
                self.assertIn(rule, self.before)
                self.assertNotIn(rule, self.after)
                # All removed exact/narrow suffix matches are covered by the
                # existing same-policy parent, including child hosts.
                host = rule.split(",", 1)[1]
                self.assertTrue(any(matches(parent, host) for parent in self.after))
                self.assertTrue(any(matches(parent, "nested." + host) for parent in self.after))

    def test_siri_and_apple_relay_already_match_apple_suffix(self) -> None:
        self.assertIn("DOMAIN-SUFFIX,apple.com", self.before)
        for host in SIRI_APPLE_HOSTS:
            with self.subTest(host=host):
                self.assertTrue(any(matches(rule, host) for rule in self.after))

    def test_candidate_diff_is_precise_and_deduplicated(self) -> None:
        self.assertEqual(
            set(self.after) - set(self.before),
            {"DOMAIN," + host for host in PCC_SHARED_HOSTS},
        )
        self.assertEqual(
            set(self.before) - set(self.after),
            set(SUPERSEDED_EDGEKEY_RULES),
        )
        self.assertEqual(len(self.after), len(set(self.after)))

    def test_private_cloud_compute_shared_hosts_are_exact(self) -> None:
        for host in PCC_SHARED_HOSTS:
            with self.subTest(host=host):
                self.assertNotIn("DOMAIN," + host, self.before)
                self.assertEqual(self.after.count("DOMAIN," + host), 1)
                self.assertTrue(any(matches(rule, host) for rule in self.after))

    def test_shared_cdn_suffixes_are_not_reclassified(self) -> None:
        self.assertNotIn("DOMAIN-SUFFIX,cloudflare.com", self.after)
        self.assertNotIn("DOMAIN-SUFFIX,fastly-edge.com", self.after)


if __name__ == "__main__":
    unittest.main()
