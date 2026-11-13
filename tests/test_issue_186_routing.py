"""Issue #186: reuse existing remote categories, without local rules or new subscriptions."""
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

    def test_existing_subscription_types_reused_without_new_local_rules(self):
        self.assertEqual(len(self.remote), 44)
        self.assertEqual([r["source_group"] for r in self.remote[:2]], ["AdBlock", "Crypto"])
        self.assertEqual(self.remote[-1]["source_group"], "ChinaDirect")
        self.assertFalse(any(r["source_group"] in {"QuarkDirect", "WikipediaDuolingo"}
                             for r in self.remote))
        self.assertFalse(any(r["policy"] in {"QuarkDirect", "WikipediaDuolingo"}
                             for r in self.remote))
        self.assertFalse(any(group["name"] in {"QuarkDirect", "WikipediaDuolingo"}
                             for group in self.model["groups"]))
        self.assertFalse(any(r["value"] in QUARK + INTERNATIONAL
                             for r in self.model["rules"]))
        self.assertNotIn("QuarkDirect.lsr", "\n".join(self.router.subscriptions))
        self.assertNotIn("WikipediaDuolingo.lsr", "\n".join(self.router.subscriptions))
        for group, policy, filename, roots in (
            ("DomesticCore", "DIRECT", "DomesticSupplement.lsr", QUARK),
            ("SharedInfrastructure", "Proxy", "SharedInfrastructure.lsr", INTERNATIONAL),
        ):
            with self.subTest(filename=filename):
                matches = [r for r in self.remote if r["uri"].endswith("/" + filename)]
                self.assertEqual(len(matches), 1)
                row = matches[0]
                self.assertEqual(row["source_group"], group)
                self.assertEqual(row["policy"], policy)
                self.assertRegex(row["uri"], r"/[0-9a-f]{40}/rules/releases/v7[.]0[.]15/" + filename.replace(".", r"[.]") + "$")
                path = ROOT / pinned_uri(row["uri"])["path"]
                content = content_rules(path.read_bytes())
                self.assertTrue({"DOMAIN-SUFFIX," + root for root in roots} <= set(content))
                self.assertEqual(len(set(content)), len(content))
                self.assertTrue(all(re.fullmatch(r"DOMAIN(?:-SUFFIX)?,[a-z0-9.-]+", r) for r in content))
                self.assertIn(str(path.relative_to(ROOT)), self.router.subscriptions)
        self.assertEqual(self.model["rules"][-2]["type"], "GEOIP")
        self.assertEqual(self.model["rules"][-1]["type"], "FINAL")

    def test_quark_direct_with_subdomain_boundaries(self):
        for domain in QUARK:
            for host in (domain, "www." + domain, "pan." + domain):
                with self.subTest(host=host):
                    decision = self.router.match(host, country="CN")
                    self.assertEqual(decision["predicted_policy"], "DIRECT")
                    self.assertIn("/DomesticSupplement.lsr", decision["first_match"]["source"])

    def test_wikipedia_and_duolingo_proxy_before_china_fallback(self):
        for domain in INTERNATIONAL:
            for host in (domain, "www." + domain):
                with self.subTest(host=host):
                    decision = self.router.match(host, country="CN")
                    self.assertEqual(decision["predicted_policy"], "Proxy")
                    self.assertIn("/SharedInfrastructure.lsr", decision["first_match"]["source"])
        for host in ("en.wikipedia.org", "upload.wikimedia.org", "www.duolingo.com"):
            self.assertEqual(self.router.match(host, country="CN")["predicted_policy"], "Proxy")

    def test_lookalikes_are_not_captured_and_prior_routes_survive(self):
        for host, unwanted_source in (
            ("notquark.cn", "/DomesticSupplement.lsr"),
            ("quark.cn.unrelated.example", "/DomesticSupplement.lsr"),
            ("notduolingo.com", "/SharedInfrastructure.lsr"),
            ("wikipedia.org.unrelated.example", "/SharedInfrastructure.lsr"),
            ("notwikipedia.org", "/SharedInfrastructure.lsr"),
        ):
            with self.subTest(host=host):
                decision = self.router.match(host)
                self.assertNotIn(unwanted_source, (decision["first_match"] or {}).get("source", ""))
        for host, policy in (
            ("raw.githubusercontent.com", "Proxy"),
            ("binance.com", "Crypto"),
            ("tiktok.com", "TikTok"),
            ("taobao.com", "DIRECT"),
        ):
            with self.subTest(host=host):
                self.assertEqual(self.router.match(host)["predicted_policy"], policy)
        china = self.router.match("duolingo.cn")
        self.assertNotIn("/SharedInfrastructure.lsr", (china["first_match"] or {}).get("source", ""))

    def test_upstream_guardrails_cover_international_sites(self):
        data = json.loads((ROOT / "rules/routing_guardrails.json").read_text(encoding="utf-8"))
        self.assertTrue(set(INTERNATIONAL) <= set(data["protected_proxy_domains"]))
        self.assertTrue(set(QUARK).isdisjoint(data["protected_proxy_domains"]))


if __name__ == "__main__":
    unittest.main()
