"""Regression tests for the optional GeoIP-based routing diagnostic profile."""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DISABLED = {
    "Our-RegionalCN", "Our-AppleOTA", "Our-Bilibili",
    "Our-Microsoft", "Our-Apple", "Our-Paypal",
}
GEOIP_OLD = "GEOIP,CN,DIRECT,no-resolve"
GEOIP_NEW = "GEOIP,CN,DIRECT"


def section(text: str, name: str) -> str:
    return text.split(f"[{name}]\n", 1)[1].split("\n[", 1)[0]


def remote_entries(text: str) -> list[str]:
    return [line for line in section(text, "Remote Rule").splitlines()
            if line.startswith("https://")]


def tag(entry: str) -> str:
    match = re.search(r"(?:^|,)\s*tag=([^,]+)", entry)
    if match is None:
        raise ValueError("remote rule is missing tag")
    return match.group(1)


def directives(text: str) -> list[str]:
    return [line for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


class TestSafeRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT / "LoonKit.lcf").read_text(encoding="utf-8")
        cls.safe = (ROOT / "LoonKit.Safe.lcf").read_text(encoding="utf-8")

    def test_only_six_composite_subscriptions_disabled(self):
        original = remote_entries(self.original)
        safe = remote_entries(self.safe)
        self.assertEqual(len(original), 37)
        self.assertEqual(len(safe), 31)
        self.assertEqual(
            safe,
            [line for line in original if tag(line) not in DISABLED],
        )
        self.assertEqual(
            set(map(tag, original)) - set(map(tag, safe)),
            DISABLED,
        )
        self.assertFalse(any("rules/hotfix/" in line for line in safe))
        self.assertFalse(any(line.startswith("AND,") for line in safe))

    def test_geoip_cn_fallback_resolves_domains(self):
        original = directives(section(self.original, "Rule"))
        safe = directives(section(self.safe, "Rule"))
        self.assertEqual(original.count(GEOIP_OLD), 1)
        self.assertEqual(safe, [GEOIP_NEW if line == GEOIP_OLD else line
                                for line in original])
        self.assertEqual(safe[-2:], [GEOIP_NEW, "FINAL,Final"])
        self.assertNotIn(GEOIP_OLD, safe)
        self.assertEqual(sum(",DIRECT" in line for line in safe), 1)

    def test_network_controls_groups_and_plugins_unchanged(self):
        for name in ("General", "Proxy", "Remote Proxy", "Remote Filter",
                     "Proxy Group", "Host", "Plugin"):
            self.assertEqual(section(self.original, name),
                             section(self.safe, name), name)
        self.assertIn("dns.alidns.com = 223.5.5.5",
                      section(self.safe, "Host"))
        self.assertEqual(
            len(re.findall(r"(?m)^https://.*[.]plugin, enabled=true$",
                           section(self.safe, "Plugin"))),
            1,
        )

    def test_no_unintended_profile_mutations(self):
        # Ignore only comments and line spacing. The profile is the formal
        # release with six subscriptions removed and a GeoIP fallback change.
        removed_lines = set(remote_entries(self.original)) - set(remote_entries(self.safe))
        baseline = [line for line in self.original.splitlines()
                    if line not in removed_lines]
        baseline = [GEOIP_NEW if line == GEOIP_OLD else line
                    for line in baseline]
        self.assertEqual(directives("\n".join(baseline)),
                         directives(self.safe))


if __name__ == "__main__":
    unittest.main()
