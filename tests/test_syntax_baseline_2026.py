"""Static compatibility contracts against Loon's 2026-09-11 official example.

The latest example contains OPTIONAL illustrative features; these tests protect
intentional omissions and fail-closed parsing, not on-device syntax acceptance.
"""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import rule_engine

MAIN = ROOT / "LoonKit.lcf"
BETA = ROOT / "beta/LoonKit.lcf"
PLUGIN = ROOT / "release/Network_Diagnostics.plugin"
DOCS = ROOT / "docs/SYNTAX_BASELINE_2026-09-11.md"


def section(data, name):
    m = re.search(r"(?m)^\[" + re.escape(name) + r"\]$", data)
    if m is None:
        raise ValueError("missing section " + name)
    rest = data[m.end():]
    next_heading = re.search(r"(?m)^\[[^]]+\]$", rest)
    return rest[:next_heading.start()] if next_heading else rest


class OfficialSyntax2026Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = MAIN.read_text(encoding="utf-8")
        cls.beta = BETA.read_text(encoding="utf-8")
        cls.plugin = PLUGIN.read_text(encoding="utf-8")
        cls.docs = DOCS.read_text(encoding="utf-8")

    def test_english_sections_and_no_demo_secrets_or_live_nodes(self):
        headings = re.findall(r"(?m)^\[([^]]+)\]$", self.beta)
        for name in ("General", "Proxy", "Remote Proxy", "Remote Filter",
                     "Proxy Group", "Rule", "Remote Rule", "Plugin"):
            self.assertIn(name, headings)
        self.assertEqual(len(headings), len(set(headings)))
        self.assertFalse([x for x in section(self.beta, "Proxy").splitlines()
                          if x.strip() and not x.lstrip().startswith("#")])
        self.assertFalse([x for x in section(self.beta, "Remote Proxy").splitlines()
                          if x.strip() and not x.lstrip().startswith("#")])
        for secret_demo in ("shadow-password", "short-id=0123456789abcdef",
                            "example.com/subscription.txt", "private-key="):
            self.assertNotIn(secret_demo, self.beta)

    def test_ali_dns_privacy_settings_were_not_replaced_by_demo(self):
        general = section(self.beta, "General")
        main = section(self.main, "General")
        expected = {
            "dns-server": "223.5.5.5,223.6.6.6",
            "doh-server": "https://dns.alidns.com/dns-query",
            "hijack-dns": "*:53",
            "ip-mode": "dual",
            "ipv6-vif": "auto",
            "udp-fallback-mode": "REJECT",
        }
        for key, value in expected.items():
            pattern = re.compile(r"(?m)^" + re.escape(key) + r"\s*=\s*(.*?)\s*$")
            match_beta = pattern.search(general)
            match_main = pattern.search(main)
            self.assertIsNotNone(match_beta, key)
            self.assertEqual(match_beta.group(1), value)
            self.assertEqual(match_beta.group(1), match_main.group(1))
        for option in ("doq-server", "doh3-server", "ssid-trigger", "resource-parser"):
            self.assertIsNone(re.search(r"(?m)^" + re.escape(option) + r"\s*=", general))
        self.assertNotIn("server:system", self.beta)

    def test_do_not_copy_example_global_direct_or_mitm(self):
        self.assertIn("GEOIP,CN,DIRECT,no-resolve", section(self.beta, "Rule"))
        self.assertIn("FINAL,Final", section(self.beta, "Rule"))
        self.assertNotIn("ssid-trigger =", self.beta)
        for forbidden in ("[MITM]", "skip-server-cert-verify = true",
                          "policy=PASS", "FINAL,DIRECT"):
            self.assertNotIn(forbidden, self.beta)

    def test_sni_assisted_ip_routing_is_feature_flagged_in_beta_only(self):
        self.assertIn("sni-sniffing = true", section(self.beta, "General"))
        self.assertIn("sni-sniffing = true", section(self.main, "General"))
        self.assertIn("GEOIP,CN,DIRECT,no-resolve", section(self.beta, "Rule"))
        self.assertIn("sni-sniffing", self.docs)

    def test_existing_diagnostics_plugin_already_uses_expression_scripts(self):
        self.assertIn("#!loon_version = 3.5.1(983)", self.plugin)
        self.assertIn("generic then script(", self.plugin)
        self.assertNotIn("network-changed then script(", self.plugin)
        self.assertNotIn("auto_check", self.plugin)
        self.assertNotIn("skip-server-cert-verify = true", self.plugin)

    def test_source_compiler_intentionally_rejects_unknown_new_types(self):
        # Loon itself supports these; do not silently normalize or misclassify
        # them in this project's deliberately narrower seven-kind compiler.
        for expression in ("DEST-PORT,443", "PROTOCOL,QUIC",
                           "AND,((PROTOCOL,UDP),(DEST-PORT,443))"):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                rule_engine.normalize(expression)
        self.assertEqual(rule_engine.normalize("DOMAIN-SUFFIX,Example.COM"),
                         "DOMAIN-SUFFIX,example.com")
        self.assertEqual(rule_engine.normalize("IP-CIDR,192.0.2.7/24"),
                         "IP-CIDR,192.0.2.0/24,no-resolve")

    def test_release_documentation_states_actual_known_boundaries(self):
        for word in ("2026-09-11", "f5b97c72dfe35283678c6da68b21c959ff30126d",
                     "784", "853", "NOT_TESTED_ON_DEVICE",
                     "local > plugin > remote", "no-resolve"):
            self.assertIn(word, self.docs)


if __name__ == "__main__":
    unittest.main()
