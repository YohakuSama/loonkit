"""Static routing safety checks for the v7.0.11 Crypto and macOS update.

These checks simulate the checked-in rule order. Real Loon on-device routing,
node selection, DNS, and remote service availability still require device logs.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from route_diagnostics import Router

EXPECTED = (
    "binance.com", "binance.us", "okx.com", "okex.com", "bybit.com",
    "bybit.eu", "bitget.com", "coinbase.com", "coinbasecdn.net",
    "kraken.com", "crypto.com", "kucoin.com", "gate.io", "gate.com",
    "mexc.com", "htx.com", "huobi.com", "bingx.com", "bitfinex.com",
    "bitstamp.net", "gemini.com", "uniswap.org", "metamask.io",
    "coingecko.com", "coinmarketcap.com", "etherscan.io",
    "bscscan.com", "defillama.com", "dexscreener.com",
)


class CryptoRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((ROOT / "build/profile.json").read_text(encoding="utf-8"))
        cls.router = Router(ROOT)

    def test_crypto_group_never_selects_direct_by_default(self):
        group, = (g for g in self.model["groups"] if g["name"] == "Crypto")
        self.assertEqual(group["type"], "select")
        self.assertEqual(group["members"], ["Proxy", "Auto", "Fallback", "ALL_Filter"])
        self.assertNotIn("DIRECT", group["members"])

    def test_domains_are_scoped_explicit_and_before_cn_fallback(self):
        declared = [r for r in self.model["rules"] if r["policy"] == "Crypto"]
        self.assertEqual(tuple(r["value"] for r in declared), EXPECTED)
        self.assertEqual(len(declared), len(set(EXPECTED)))
        self.assertTrue(all(r["type"] == "DOMAIN-SUFFIX" and r["flags"] == [] for r in declared))
        self.assertTrue(all(r["type"] != "DOMAIN-KEYWORD" for r in declared))
        fallback = next(i for i, r in enumerate(self.model["rules"]) if r["type"] == "GEOIP")
        self.assertTrue(all(self.model["rules"].index(r) < fallback for r in declared))
        self.assertEqual(self.model["rules"][-2]["policy"], "DIRECT")
        self.assertEqual(self.model["rules"][-1]["type"], "FINAL")

    def test_crypto_domains_and_subdomains_do_not_route_cn_direct(self):
        for domain in EXPECTED:
            for hostname in (domain, "api." + domain):
                with self.subTest(host=hostname):
                    result = self.router.match(hostname, country="CN")
                    self.assertEqual(result["predicted_policy"], "Crypto")
                    self.assertEqual(result["first_match"]["source"], "本地规则")

    def test_no_broad_keyword_or_similar_lookalike_capture(self):
        for hostname in ("notbinance.com", "fakeokx.com", "crypto.com.evil.example",
                         "coinbase.com.cn", "uniswap.org.fake.example"):
            with self.subTest(host=hostname):
                self.assertNotEqual(self.router.match(hostname)["predicted_policy"], "Crypto")

    def test_published_plugin_explicitly_supports_macOS(self):
        source = (ROOT / "src/diagnostics/Network_Diagnostics.plugin").read_text(encoding="utf-8")
        published = (ROOT / "release/Network_Diagnostics.plugin").read_text(encoding="utf-8")
        for body in (source, published):
            self.assertIn("#!system = iOS,iPadOS,macOS", body)
            self.assertIn("#!loon_version = 3.5.1(983)", body)
            self.assertEqual(body.count("generic then script("), 3)
        self.assertIn("macOS", (ROOT / "docs/NETWORK_DIAGNOSTICS.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
