"""Protect LoonKit's fixed group layout and balanced multi-subscription selection."""
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "LoonKit.lcf"
EXPECTED_GROUPS = (
    "Proxy", "Auto", "Fallback", "AdBlock", "Final", "AI", "Google",
    "Microsoft", "Apple", "YouTube", "Netflix", "Disney", "PrimeVideo",
    "Spotify", "TikTok", "Twitch", "HBO", "Abema", "動畫瘋", "Dazn",
    "BBC", "Bilibili", "Telegram", "Whatsapp", "Instagram", "Facebook",
    "Twitter", "Discord", "Line", "Reddit", "Linkedin", "Steam", "Paypal",
)


def get_section(profile, heading):
    match = re.search(r"(?m)^\[" + re.escape(heading) + r"\]$", profile)
    if not match:
        raise AssertionError("Missing Loon section " + heading)
    rest = profile[match.end():]
    next_section = re.search(r"(?m)^\[[^\]]+\]$", rest)
    return rest[:next_section.start()] if next_section else rest


def settings(section):
    return {key.strip(): value.strip()
            for line in section.splitlines() if line.strip() and not line.lstrip().startswith("#")
            for key, sep, value in [line.partition("=")] if sep}


class PolicySelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = PROFILE.read_text(encoding="utf-8")
        cls.groups = settings(get_section(cls.profile, "Proxy Group"))
        cls.filters = settings(get_section(cls.profile, "Remote Filter"))
        cls.general = settings(get_section(cls.profile, "General"))

    def test_no_new_or_removed_strategy_groups(self):
        self.assertEqual(tuple(self.groups), EXPECTED_GROUPS)
        self.assertEqual(len(self.groups), 33)

    def test_filters_isolate_manual_and_automatic_candidates(self):
        for name in ("ALL_Filter", "Auto_Filter", "Fallback_Filter"):
            self.assertEqual(self.filters[name], 'NameRegex, FilterKey = ".*"')
        self.assertTrue(self.groups["Proxy"].startswith("select,Auto,Fallback,ALL_Filter,"))
        self.assertTrue(self.groups["Auto"].startswith("url-test,Auto_Filter,"))
        self.assertTrue(self.groups["Fallback"].startswith("fallback,Fallback_Filter,"))
        # All existing service selectors retain manual/auto/fallback access.
        for name in EXPECTED_GROUPS:
            if name in ("Proxy", "Auto", "Fallback", "AdBlock", "Final"):
                continue
            self.assertIn("ALL_Filter", self.groups[name], name)

    def test_native_probe_address_is_consistent(self):
        probe = "http://www.bing.com"
        self.assertEqual(self.general["proxy-test-url"], probe)
        for name in ("Auto", "Fallback"):
            self.assertIn("url = " + probe, self.groups[name])
            self.assertNotIn("generate_204", self.groups[name])
        self.assertEqual(self.general["internet-test-url"],
                         "http://wifi.vivo.com.cn/generate_204")
        self.assertEqual(self.general["test-timeout"], "5")

    def test_balanced_intervals_and_failover_threshold(self):
        self.assertIn("interval = 600", self.groups["Auto"])
        self.assertIn("tolerance = 60", self.groups["Auto"])
        self.assertIn("interval = 900", self.groups["Fallback"])
        self.assertIn("max-timeout = 2200", self.groups["Fallback"])

    def test_small_and_large_subscription_names_have_no_default_exclusions(self):
        # Static filter-regex regression, not an actual Loon network performance test.
        for size in (1, 6, 120):
            nodes = [f"Airport-{(i % 3) + 1}-节点-{i}" for i in range(size)]
            for name in ("ALL_Filter", "Auto_Filter", "Fallback_Filter"):
                pattern = self.filters[name].split('FilterKey = "', 1)[1].rstrip('"')
                matched = [node for node in nodes if re.search(pattern, node)]
                self.assertEqual(matched, nodes, (size, name))
        self.assertEqual(self.profile.splitlines()[0], "# LoonKit v6.5.10")

    def test_auto_prioritizes_latency_and_fallback_uses_order(self):
        # Confirm group strategy semantics; Loon makes actual runtime decisions.
        self.assertTrue(self.groups["Auto"].startswith("url-test,"))
        self.assertTrue(self.groups["Fallback"].startswith("fallback,"))
        self.assertNotIn("max-timeout =", self.groups["Auto"])
        self.assertNotIn("tolerance =", self.groups["Fallback"])

    def test_promoted_active_directives_match_frozen_candidate(self):
        import hashlib
        active = "\n".join(line for line in self.profile.splitlines()
                           if line.strip() and not line.lstrip().startswith("#")) + "\n"
        self.assertEqual(hashlib.sha256(active.encode("utf-8")).hexdigest(),
                         __import__('json').loads((ROOT/'build/release_spec.json').read_text())['current_runtime_directives_sha256'])

    def test_no_internal_candidate_or_audit_comments_in_profile(self):
        comment_lines = [line for line in self.profile.splitlines()
                         if line.lstrip().startswith("#")]
        joined = "\n".join(comment_lines).lower()
        for word in ("candidate only", "pre-migration", "reviewed local", "fallback routes",
                     "提示两条", "两条检测路线"):
            self.assertNotIn(word, joined)

    def test_dns_mode(self):
        self.assertEqual(self.general["domain-reject-mode"],"DNS")
        self.assertEqual(self.general["dns-reject-mode"],"LOOPBACKIP")

    def test_dns_routes_and_plugin_are_unchanged_in_scope(self):
        rules = get_section(self.profile, "Rule")
        self.assertIn("GEOIP,CN,DIRECT,no-resolve", rules)
        self.assertIn("FINAL,Final", rules)
        self.assertEqual(len([x for x in get_section(self.profile, "Plugin").splitlines()
                              if x.startswith("https://") and ".plugin" in x]), 1)


if __name__ == "__main__":
    unittest.main()
