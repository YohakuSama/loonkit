"""Strict v6.5.8 one-variable isolation for six suspect Loon GEOIP rule subscriptions.

These profiles are NOT a fix. Device runs determine the offending individual
subscription or whether a combination of subscriptions triggers VPN restarts.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / "diagnostics/v6.5.8-geoip-six"
SUSPECTS = ("RegionalCN", "AppleOTA", "Bilibili",
            "Microsoft", "Apple", "Paypal")
GROUPS = {
    "GroupA": SUSPECTS[:3],
    "GroupB": SUSPECTS[3:],
    **{"Only" + item: (item,) for item in SUSPECTS},
}


def remote_tag(line: str) -> str | None:
    if not line.startswith("https://") or ", policy=" not in line:
        return None
    hit = re.search(r"(?:^|,)\s*tag=Our-([^,]+)", line)
    return hit.group(1) if hit else None


def directives(text: str) -> list[str]:
    return [line for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def remote_entries(text: str) -> list[str]:
    return [line for line in text.split("[Remote Rule]\n", 1)[1]
            .split("\n[", 1)[0].splitlines() if line.startswith("https://")]


def section(text: str, name: str) -> str:
    return text.split("[" + name + "]\n", 1)[1].split("\n[", 1)[0]


class TestV658SixIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT / "LoonKit.lcf").read_text(encoding="utf-8")
        cls.base_entries = remote_entries(cls.original)

    def test_baseline_six_present(self):
        self.assertEqual(len(self.base_entries), 37)
        self.assertEqual(
            [remote_tag(line) for line in self.base_entries
             if remote_tag(line) in SUSPECTS], list(SUSPECTS),
        )
        self.assertEqual(
            directives(section(self.original, "Rule"))[-2:],
            ["GEOIP,CN,DIRECT,no-resolve", "FINAL,Final"],
        )

    def test_each_profile_only_removes_unselected_remote_entries(self):
        all_suspects = set(SUSPECTS)
        for profile_name, selected in GROUPS.items():
            with self.subTest(profile=profile_name):
                text = (FILES / f"{profile_name}.lcf").read_text(
                    encoding="utf-8"
                )
                active = set(selected)
                removed = all_suspects - active
                expected_entries = [
                    row for row in self.base_entries
                    if remote_tag(row) not in removed
                ]
                self.assertEqual(remote_entries(text), expected_entries)
                self.assertEqual(
                    len(expected_entries), 31 + len(selected),
                )
                expected_directives = [
                    row for row in self.original.splitlines()
                    if remote_tag(row) not in removed
                ]
                self.assertEqual(
                    directives(text),
                    directives("\n".join(expected_directives)),
                )
                for part in ("General", "Proxy", "Remote Proxy",
                             "Remote Filter", "Proxy Group", "Host",
                             "Rule", "Plugin"):
                    self.assertEqual(
                        section(text, part), section(self.original, part),
                    )
                self.assertEqual(
                    directives(section(text, "Rule"))[-2:],
                    ["GEOIP,CN,DIRECT,no-resolve", "FINAL,Final"],
                )
                self.assertNotIn(
                    "\nGEOIP,CN,DIRECT\nFINAL,Final\n", text
                )

    def test_groups_are_complementary_and_singles_cover_every_suspect(self):
        self.assertEqual(
            set(GROUPS["GroupA"]) | set(GROUPS["GroupB"]),
            set(SUSPECTS),
        )
        self.assertFalse(
            set(GROUPS["GroupA"]) & set(GROUPS["GroupB"]),
        )
        self.assertEqual(
            {GROUPS[name][0] for name in GROUPS if name.startswith("Only")},
            set(SUSPECTS),
        )


if __name__ == "__main__":
    unittest.main()
