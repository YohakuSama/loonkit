"""LoonKit's independent Crypto subscription: scope, precedence and safety."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from loon_resources import content_rules, pinned_uri
from route_diagnostics import Router

ORIGINAL = (
    "binance.com", "binance.us", "okx.com", "okex.com", "bybit.com",
    "bybit.eu", "bitget.com", "coinbase.com", "coinbasecdn.net",
    "kraken.com", "crypto.com", "kucoin.com", "gate.io", "gate.com",
    "mexc.com", "htx.com", "huobi.com", "bingx.com", "bitfinex.com",
    "bitstamp.net", "gemini.com", "uniswap.org", "metamask.io",
    "coingecko.com", "coinmarketcap.com", "etherscan.io",
    "bscscan.com", "defillama.com", "dexscreener.com",
)
MODERN = (
    "hyperliquid.xyz", "phantom.com", "solscan.io", "ledger.com",
    "aave.com", "pancakeswap.finance", "raydium.io", "ethereum.org",
    "solana.com", "trezor.io", "polygonscan.com", "sui.io",
    "lido.fi", "walletconnect.com", "rabby.io", "chain.link",
)
BLOCKED_TELEMETRY = (
    "openvpn.f2pool.com", "fdt.kraken.com", "gen.etherscan.io",
    "ingest.coincodex.com", "metrics.hyperliquid.xyz",
    "mixpanel-proxy.coingecko.com", "nasi.etherscan.com",
    "pages.ledger.com",
)


class CryptoRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((ROOT / "build/profile.json").read_text(encoding="utf-8"))
        cls.router = Router(ROOT)
        cls.remote = next(r for r in cls.model["remote_rules"] if r["policy"] == "Crypto")
        cls.path = ROOT / pinned_uri(cls.remote["uri"])["path"]
        cls.rules = content_rules(cls.path.read_bytes())
        cls.suffix = {r.partition(",")[2] for r in cls.rules if r.startswith("DOMAIN-SUFFIX,")}
        cls.exact = {r.partition(",")[2] for r in cls.rules if r.startswith("DOMAIN,")}

    def test_crypto_finance_group_order_and_unique_icon(self):
        groups = self.model["groups"]
        names = [g["name"] for g in groups]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names[:5], ["Proxy", "Auto", "Fallback", "AdBlock", "Final"])
        self.assertEqual(names[names.index("Speedtest") + 1:names.index("Speedtest") + 3],
                         ["Crypto", "Paypal"])
        self.assertEqual(names[names.index("Paypal") + 1], "YouTube")
        crypto, = (g for g in groups if g["name"] == "Crypto")
        self.assertRegex(crypto["icon"], r"/[a-f0-9]{40}/icons/Crypto[.]png$")
        self.assertNotEqual(crypto["icon"], groups[0]["icon"])
        img = (ROOT / "icons/Crypto.png").read_bytes()
        self.assertEqual(img[:8].hex(), "89504e470d0a1a0a")
        self.assertEqual(struct.unpack(">II", img[16:24]), (512, 512))

    def test_crypto_group_never_selects_direct_by_default(self):
        group, = (g for g in self.model["groups"] if g["name"] == "Crypto")
        self.assertEqual(group["type"], "select")
        self.assertEqual(group["members"], ["Proxy", "Auto", "Fallback", "ALL_Filter"])
        self.assertNotIn("DIRECT", group["members"])

    def test_remote_only_no_embedded_crypto_and_precedence(self):
        self.assertFalse(any(r["policy"] == "Crypto" for r in self.model["rules"]))
        self.assertFalse(any(",Crypto" in line for line in self.router.sections["Rule"]))
        remote = self.model["remote_rules"]
        self.assertEqual(len(remote), 44)
        self.assertEqual([r["source_group"] for r in remote[:2]], ["AdBlock", "Crypto"])
        self.assertEqual(remote[-1]["source_group"], "ChinaDirect")
        self.assertEqual(self.remote["tag"], "Our-Crypto")
        self.assertEqual(self.remote["source_group"], "Crypto")
        self.assertRegex(self.remote["uri"], r"/[0-9a-f]{40}/rules/releases/v7[.]0[.]13/Crypto[.]lsr$")
        self.assertIn("rules/releases/v7.0.13/Crypto.lsr", self.router.subscriptions)
        self.assertTrue(self.path.is_file())
        self.assertEqual(self.model["rules"][-2]["policy"], "DIRECT")
        self.assertEqual(self.model["rules"][-1]["type"], "FINAL")

    def test_reviewed_asset_has_no_duplicate_wide_or_dominated_rules(self):
        self.assertEqual(len(self.rules), 219)
        self.assertEqual(len(self.rules), len(set(self.rules)))
        self.assertEqual(len(self.suffix), 218)
        self.assertEqual(self.exact, {"token-api.metaswap.codefi.network"})
        self.assertTrue(all(r.startswith(("DOMAIN,", "DOMAIN-SUFFIX,")) for r in self.rules))
        for domain in self.suffix:
            with self.subTest(domain=domain):
                self.assertFalse(any(domain != parent and domain.endswith("." + parent)
                                     for parent in self.suffix))
        for forbidden in ("crunchbase.com", "tradingview.com", "ipfs.io",
                          "liquid.com", "ftx.com", "bittrex.com", "localbitcoins.com"):
            self.assertNotIn(forbidden, self.suffix)
        self.assertIn("blackmatrix7/ios_rule_script", self.path.read_text(encoding="utf-8"))

    def test_old_and_new_platforms_are_proxy_first_even_with_cn_geoip(self):
        self.assertTrue(set(ORIGINAL + MODERN) <= self.suffix)
        for domain in sorted(self.suffix):
            for host in (domain, "api." + domain):
                with self.subTest(host=host):
                    decision = self.router.match(host, country="CN")
                    self.assertEqual(decision["predicted_policy"], "Crypto")
                    self.assertIn("/Crypto.lsr", decision["first_match"]["source"])
        self.assertEqual(self.router.match("token-api.metaswap.codefi.network")["predicted_policy"], "Crypto")
        self.assertEqual(self.router.match("mdex.co", country="CN")["predicted_policy"], "Crypto")
        self.assertEqual(self.router.match("mdex.com", country="CN")["predicted_policy"], "Crypto")

    def test_adblock_telemetry_keeps_priority_and_coincheck_is_not_blocked(self):
        adblock = self.model["remote_rules"][0]
        adpath = ROOT / pinned_uri(adblock["uri"])["path"]
        original = (ROOT / "rules/releases/v7.0.3/AdBlockBalanced.lsr").read_text(encoding="utf-8")
        reviewed = adpath.read_text(encoding="utf-8")
        self.assertEqual(original.count("DOMAIN,coincheck.com\n"), 1)
        self.assertEqual(reviewed, original.replace("DOMAIN,coincheck.com\n", ""))
        for host in BLOCKED_TELEMETRY:
            with self.subTest(host=host):
                decision = self.router.match(host, country="CN")
                self.assertEqual(decision["predicted_policy"], "AdBlock")
                self.assertIn("/AdBlockBalanced.lsr", decision["first_match"]["source"])
        for host in ("coincheck.com", "www.coincheck.com"):
            with self.subTest(host=host):
                self.assertEqual(self.router.match(host)["predicted_policy"], "Crypto")

    def test_no_broad_keyword_or_similar_lookalike_capture(self):
        for hostname in ("notbinance.com", "fakeokx.com", "crypto.com.evil.example",
                         "coinbase.com.cn", "uniswap.org.fake.example",
                         "random-binance-example.com", "notmetamask.com"):
            with self.subTest(host=hostname):
                self.assertNotEqual(self.router.match(hostname)["predicted_policy"], "Crypto")
        for domain, policy in (("gemini.google.com", "Gemini"),
                               ("tiktok.com", "TikTok"),
                               ("raw.githubusercontent.com", "Proxy")):
            with self.subTest(host=domain):
                self.assertEqual(self.router.match(domain)["predicted_policy"], policy)

    def test_upstream_direct_guardrails_cover_crypto_roots(self):
        data = json.loads((ROOT / "rules/routing_guardrails.json").read_text(encoding="utf-8"))
        protected = data["protected_proxy_domains"]
        self.assertEqual(len(protected), len(set(protected)))
        self.assertTrue(self.suffix <= set(protected))

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
