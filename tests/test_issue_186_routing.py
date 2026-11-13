"""Issue #186: scoped Quark DIRECT and Wikipedia/Duolingo proxy routing."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from loon_resources import content_rules, pinned_uri
from route_diagnostics import Router

QUARK = ("quark.cn", "myquark.cn")
INTERNATIONAL = (
    "duolingo.com", "mediawiki.org", "w.wiki", "wikibooks.org",
    "wikidata.org", "wikimedia.org", "wikimediafoundation.org",
    "wikinews.org", "wikipedia.org", "wikiquote.org",
    "wikisource.org", "wikiversity.org", "wikivoyage.org",
    "wiktionary.org", "wmfusercontent.org",
)


class Issue186RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((ROOT / "build/profile.json").read_text(encoding="utf-8"))
        cls.router = Router(ROOT)
        cls.remote = cls.model["remote_rules"]

    def test_scoped_immutable_subscriptions_and_precedence(self):
        self.assertEqual(len(self.remote), 46)
        self.assertEqual([r["source_group"] for r in self.remote[:4]],
                         ["AdBlock", "Crypto", "QuarkDirect", "WikipediaDuolingo"])
        self.assertEqual(self.remote[-1]["source_group"], "ChinaDirect")
        for name, policy, domains in (
            ("QuarkDirect", "DIRECT", QUARK),
            ("WikipediaDuolingo", "Proxy", INTERNATIONAL),
        ):
            with self.subTest(name=name):
                row, = (r for r in self.remote if r["source_group"] == name)
                self.assertEqual(row["policy"], policy)
                self.assertRegex(row["uri"], r"/[0-9a-f]{40}/rules/releases/v7[.]0[.]14/" + name + r"[.]lsr$")
                path = ROOT / pinned_uri(row["uri"])["path"]
                rules = content_rules(path.read_bytes())
                self.assertEqual(set(rules), {"DOMAIN-SUFFIX," + d for d in domains})
                self.assertEqual(len(rules), len(domains))
                self.assertIn("rules/releases/v7.0.14/" + name + ".lsr", self.router.subscriptions)
                self.assertTrue(all(re.fullmatch(r"DOMAIN-SUFFIX,[a-z0-9.-]+", rule) for rule in rules))
        self.assertEqual(self.model["rules"][-2]["type"], "GEOIP")
        self.assertEqual(self.model["rules"][-1]["type"], "FINAL")

    def test_quark_direct_even_for_subdomains(self):
        for domain in QUARK:
            for host in (domain, "www." + domain, "pan." + domain):
                with self.subTest(host=host):
                    result = self.router.match(host, country="CN")
                    self.assertEqual(result["predicted_policy"], "DIRECT")
                    self.assertIn("/QuarkDirect.lsr", result["first_match"]["source"])

    def test_international_services_proxy_before_domestic_fallback(self):
        for domain in INTERNATIONAL:
            for host in (domain, "www." + domain):
                with self.subTest(host=host):
                    result = self.router.match(host, country="CN")
                    self.assertEqual(result["predicted_policy"], "Proxy")
                    self.assertIn("/WikipediaDuolingo.lsr", result["first_match"]["source"])
        for host in ("en.wikipedia.org", "upload.wikimedia.org", "www.duolingo.com"):
            self.assertEqual(self.router.match(host, country="CN")["predicted_policy"], "Proxy")

    def test_no_broad_keyword_capture_and_existing_routes(self):
        for host, unwanted_source in (
            ("notquark.cn", "/QuarkDirect.lsr"),
            ("quark.cn.unrelated.example", "/QuarkDirect.lsr"),
            ("notduolingo.com", "/WikipediaDuolingo.lsr"),
            ("wikipedia.org.unrelated.example", "/WikipediaDuolingo.lsr"),
            ("notwikipedia.org", "/WikipediaDuolingo.lsr"),
        ):
            with self.subTest(host=host):
                result = self.router.match(host)
                self.assertNotIn(unwanted_source, (result["first_match"] or {}).get("source", ""))
        for host, policy in (
            ("raw.githubusercontent.com", "Proxy"),
            ("binance.com", "Crypto"),
            ("tiktok.com", "TikTok"),
            ("taobao.com", "DIRECT"),
        ):
            with self.subTest(host=host):
                self.assertEqual(self.router.match(host)["predicted_policy"], policy)
        # This update does not alter the China locale of Duolingo or force it via international rules.
        locale = self.router.match("duolingo.cn")
        self.assertNotIn("/WikipediaDuolingo.lsr", (locale["first_match"] or {}).get("source", ""))

    def test_proxy_domains_protected_in_upstream_review(self):
        data = json.loads((ROOT / "rules/routing_guardrails.json").read_text(encoding="utf-8"))
        self.assertTrue(set(INTERNATIONAL) <= set(data["protected_proxy_domains"]))
        self.assertTrue(set(QUARK).isdisjoint(data["protected_proxy_domains"]))


if __name__ == "__main__":
    unittest.main()
