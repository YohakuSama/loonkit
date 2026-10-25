"""Verify bounded Loon GEOIP composites preserve all six v6.5.8 source matchers.

This is a static/Boolean equivalence check; real iOS Network Extension
stability and DNS-leak outcomes require device-side testing.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("RegionalCN", "AppleOTA", "Bilibili", "Microsoft", "Apple", "Paypal")
PIN = "ec84df35613c56d01639cd0140307148af0d1258"
ROOT_DIR = Path("rules/experiments/v6.5.8-geoip-batched")
PLAIN = re.compile(
    r"^AND,\(\((DOMAIN(?:-SUFFIX)?|IP-CIDR6?|IP-ASN,[^()]+|IP-CIDR,[^()]+),([^()]+)\),"
    r"\((GEOIP,CN|NOT,\(\(GEOIP,CN\)\))\)\)$"
)
# The normalized child matcher may include a comma (CIDR no-resolve).
SINGLE = re.compile(
    r"^AND,\(\(((?:DOMAIN|DOMAIN-SUFFIX|IP-CIDR|IP-CIDR6|IP-ASN),[^()]+)\),"
    r"\((GEOIP,CN|NOT,\(\(GEOIP,CN\)\))\)\)$"
)
GROUP = re.compile(
    r"^AND,\(\(OR,\(\((.*)\)\)\),"
    r"\((GEOIP,CN|NOT,\(\(GEOIP,CN\)\))\)\)$"
)
MATCHER = re.compile(r"^(DOMAIN|DOMAIN-SUFFIX|IP-CIDR|IP-CIDR6|IP-ASN),[^()]+$")


def rules(path: Path) -> list[str]:
    return [row for row in path.read_text(encoding="utf-8").splitlines()
            if row and not row.startswith("#")]


def parse(row: str) -> list[tuple[str, str]]:
    one = SINGLE.fullmatch(row)
    if one:
        return [(one.group(1), one.group(2))]
    group = GROUP.fullmatch(row)
    if not group:
        raise ValueError("unrecognized logic expression: " + row[:200])
    children = group.group(1).split("),(")
    if not 2 <= len(children) <= 8:
        raise ValueError("group is outside conservative 2..8 bound")
    if any(not MATCHER.fullmatch(child) or child.startswith("IP-")
           for child in children):
        raise ValueError("OR grouping is restricted to domain matchers")
    return [(child, group.group(2)) for child in children]


def remote(text: str) -> list[str]:
    return [line for line in text.split("[Remote Rule]\n", 1)[1]
            .split("\n[", 1)[0].splitlines() if line.startswith("https://")]


def tag(line: str) -> str:
    match = re.search(r"(?:^|,)\s*tag=([^,]+)", line)
    if match is None:
        raise ValueError("missing remote tag")
    return match.group(1)


class TestCompositeGeoIPBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stable = (ROOT / "LoonKit.lcf").read_text(encoding="utf-8")
        cls.candidate = (ROOT / "LoonKit.CompositeFix.lcf").read_text(encoding="utf-8")

    def test_every_source_matcher_and_geoip_polarity_preserved(self):
        totals = []
        for name in NAMES:
            before = rules(ROOT / f"rules/releases/v6.5.8/{name}.list")
            after = rules(ROOT / ROOT_DIR / f"{name}.list")
            expected = [entry for row in before for entry in parse(row)]
            observed = [entry for row in after for entry in parse(row)]
            self.assertEqual(expected, observed, name)
            self.assertLessEqual(len(after), len(before), name)
            self.assertTrue(any("(OR," in row for row in after), name)
            totals.append((len(before), len(after)))
            # OR only redistributes OR over AND with the same immutable
            # GEOIP condition: (a AND g) OR (b AND g) = (a OR b) AND g.
            for row in after:
                parts = parse(row)
                for geo_cn in (False, True):
                    for term in range(len(parts)):
                        individual = any(
                            (i == term) and (geo_cn == (geo == "GEOIP,CN"))
                            for i, (_, geo) in enumerate(parts)
                        )
                        grouped = (
                            (geo_cn == (parts[0][1] == "GEOIP,CN"))
                            and any(i == term for i in range(len(parts)))
                        )
                        self.assertEqual(individual, grouped)
        self.assertEqual(sum(x[0] for x in totals), 5228)
        self.assertLess(sum(x[1] for x in totals), 1000)

    def test_six_subscriptions_still_enabled_and_no_other_profile_changes(self):
        before = remote(self.stable)
        after = remote(self.candidate)
        self.assertEqual(len(before), 37)
        self.assertEqual(len(after), 37)
        self.assertEqual([tag(row) for row in before],
                         [tag(row) for row in after])
        for a, b in zip(before, after):
            name = tag(a).removeprefix("Our-")
            if name in NAMES:
                expected = (
                    "https://raw.githubusercontent.com/YohakuSama/loonkit/"
                    f"{PIN}/{ROOT_DIR.as_posix()}/{name}.list"
                )
                self.assertEqual(b.split(",", 1)[0], expected)
                self.assertEqual(b.split(",", 1)[1], a.split(",", 1)[1])
                self.assertIn("enabled=true", b)
            else:
                self.assertEqual(a, b)
        changed = set(before) - set(after)
        self.assertEqual(len(changed), 6)
        # Nothing after Remote Rule is changed; General, Groups and other
        # profile directives before Remote Rule are also byte-for-byte equal.
        self.assertEqual(
            self.stable.split("[Remote Rule]", 1)[0].splitlines()[2:],
            self.candidate.split("[Remote Rule]", 1)[0].splitlines()[3:],
        )
        self.assertEqual(
            self.stable.split("\n[Host]", 1)[1],
            self.candidate.split("\n[Host]", 1)[1],
        )
        self.assertIn("\nGEOIP,CN,DIRECT,no-resolve\nFINAL,Final\n",
                      self.candidate)
        self.assertIn("doh-server = https://dns.alidns.com/dns-query",
                      self.candidate)
        self.assertNotIn("\nGEOIP,CN,DIRECT\nFINAL,Final", self.candidate)


if __name__ == "__main__":
    unittest.main()
