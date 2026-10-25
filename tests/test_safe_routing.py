"""Confirm A/B diagnostic changes only six target subscriptions."""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DISABLED = {
    "Our-RegionalCN", "Our-AppleOTA", "Our-Bilibili",
    "Our-Microsoft", "Our-Apple", "Our-Paypal",
}
GEOIP_BASE = "GEOIP,CN,DIRECT,no-resolve"


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

    def test_only_six_subscriptions_removed(self):
        original = remote_entries(self.original)
        safe = remote_entries(self.safe)
        self.assertEqual(len(original), 37)
        self.assertEqual(len(safe), 31)
        self.assertEqual(safe, [
            line for line in original if tag(line) not in DISABLED
        ])
        self.assertEqual(set(map(tag, original)) - set(map(tag, safe)), DISABLED)
        self.assertFalse(any("rules/hotfix/" in line for line in safe))

    def test_geoip_dns_and_network_configuration_unchanged(self):
        for name in ("General", "Proxy", "Remote Proxy", "Remote Filter",
                     "Proxy Group", "Host", "Rule", "Plugin"):
            self.assertEqual(
                section(self.original, name),
                section(self.safe, name),
                name,
            )
        self.assertEqual(
            directives(section(self.safe, "Rule"))[-2:],
            [GEOIP_BASE, "FINAL,Final"],
        )
        self.assertIn("dns.alidns.com = 223.5.5.5",
                      section(self.safe, "Host"))
        self.assertEqual(
            len(re.findall(r"(?m)^https://.*[.]plugin, enabled=true$",
                           section(self.safe, "Plugin"))), 1,
        )

    def test_diagnostic_groups_split_original_six_and_nothing_else(self):
        halves = {
            "A": {"Our-RegionalCN", "Our-AppleOTA", "Our-Bilibili"},
            "B": {"Our-Microsoft", "Our-Apple", "Our-Paypal"},
        }
        self.assertEqual(halves["A"] | halves["B"], DISABLED)
        self.assertFalse(halves["A"] & halves["B"])
        original_entries = remote_entries(self.original)
        for letter, keep in halves.items():
            profile = (ROOT / f"diagnostics/v6.5.8/Group{letter}.lcf").read_text(
                encoding="utf-8"
            )
            expected = [line for line in original_entries
                        if tag(line) not in (DISABLED - keep)]
            self.assertEqual(remote_entries(profile), expected)
            self.assertEqual(len(remote_entries(profile)), 34)
            removed = set(original_entries) - set(expected)
            self.assertEqual(
                directives("\\n".join(line for line in self.original.splitlines()
                                      if line not in removed)),
                directives(profile),
            )
            for name in ("General", "Proxy Group", "Host", "Rule", "Plugin"):
                self.assertEqual(section(self.original, name),
                                 section(profile, name))

    def test_profile_identical_except_six_entries_and_comments(self):
        removed = set(remote_entries(self.original)) - set(remote_entries(self.safe))
        expected = [line for line in self.original.splitlines()
                    if line not in removed]
        self.assertEqual(directives("\n".join(expected)), directives(self.safe))


if __name__ == "__main__":
    unittest.main()
