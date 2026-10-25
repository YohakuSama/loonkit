"""Regression checks for the optional non-composite Loon routing profile."""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PIN = "ead898c87aebf68563cccc0263e9e02665d05f3a"
HOTFIX = "rules/hotfix/v6.5.8-safe/"
NAMES = ("RegionalCN", "AppleOTA", "Bilibili", "Microsoft", "Apple", "Paypal")
TAGS = {f"Our-{name}": name for name in NAMES}
CHILD = re.compile(
    r"^AND,\(\(((?:DOMAIN|DOMAIN-SUFFIX|IP-CIDR|IP-CIDR6|IP-ASN),[^()]+)\),"
    r"\((?:GEOIP,CN|NOT,\(\(GEOIP,CN\)\))\)\)$"
)
PLAIN = re.compile(r"^(DOMAIN|DOMAIN-SUFFIX|IP-CIDR|IP-CIDR6|IP-ASN),[^,]+(?:,no-resolve)?$")


def rules(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def remote(profile: str) -> list[str]:
    return profile.split("[Remote Rule]\n", 1)[1].split("\n[", 1)[0].strip().splitlines()


def tag(line: str) -> str:
    return re.search(r"(?:^|,)\s*tag=([^,]+)", line).group(1)


class TestSafeRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = (ROOT / "LoonKit.lcf").read_text(encoding="utf-8")
        cls.profile = (ROOT / "LoonKit.Safe.lcf").read_text(encoding="utf-8")

    def test_six_subscriptions_replaced_only(self):
        baseline, safe = remote(self.baseline), remote(self.profile)
        self.assertEqual(len(baseline), 37)
        self.assertEqual(len(safe), 37)
        self.assertEqual([tag(line) for line in baseline], [tag(line) for line in safe])
        changed = [tag(a) for a, b in zip(baseline, safe) if a != b]
        self.assertCountEqual(changed, TAGS)
        self.assertEqual(
            self.baseline.split("[Remote Rule]", 1)[0].splitlines()[2:],
            self.profile.split("[Remote Rule]", 1)[0].splitlines()[4:],
        )
        self.assertEqual(self.baseline.split("\n[Host]", 1)[1],
                         self.profile.split("\n[Host]", 1)[1])

        for line in safe:
            name = TAGS.get(tag(line))
            if name:
                self.assertTrue(line.startswith(
                    f"https://raw.githubusercontent.com/YohakuSama/loonkit/{PIN}/"
                    f"{HOTFIX}{name}.list, policy="))
                policy = "DIRECT" if name in ("RegionalCN", "AppleOTA") else name
                self.assertIn(f", policy={policy},", line)
                self.assertIn(", enabled=true", line)

    def test_plain_matcher_coverage_and_no_logical_geoip(self):
        for name in NAMES:
            source = rules(ROOT / f"rules/releases/v6.5.8/{name}.list")
            compiled = rules(ROOT / HOTFIX / f"{name}.list")
            self.assertTrue(compiled)
            self.assertEqual(len(set(compiled)), len(compiled))
            self.assertTrue(all(PLAIN.fullmatch(line) for line in compiled), name)
            self.assertFalse(any(line.startswith(("AND,", "NOT,", "OR,", "GEOIP,"))
                                 for line in compiled))
            source_children = []
            for line in source:
                match = CHILD.fullmatch(line)
                self.assertIsNotNone(match, f"{name}: {line[:100]}")
                source_children.append(match.group(1))
            if name == "RegionalCN":
                roots = {"acg.tv", "b23.tv", "biliapi.com", "biliapi.net",
                         "bilibili.com", "bilibili.cn", "bilivideo.com",
                         "hdslb.com", "biligame.com", "bilibilipay.com"}
                expected = {
                    line for line in source_children
                    if line.startswith(("DOMAIN,", "DOMAIN-SUFFIX,"))
                    and line.split(",", 1)[1].endswith(".cn")
                }
                expected.update(f"DOMAIN-SUFFIX,{root}" for root in roots)
                self.assertEqual(set(compiled), expected)
                self.assertNotIn("GEOIP,CN", "\n".join(compiled))
            else:
                self.assertEqual(compiled, source_children, name)

    def test_precedence_and_network_defaults(self):
        ordered = [tag(row) for row in remote(self.profile)]
        for owner in ("Our-AppleOTA", "Our-Bilibili", "Our-Microsoft",
                      "Our-Apple", "Our-Paypal"):
            self.assertLess(ordered.index("Our-RegionalCN"), ordered.index(owner))
        self.assertLess(ordered.index("Our-AppleOTA"), ordered.index("Our-Apple"))
        self.assertIn("GEOIP,CN,DIRECT,no-resolve", self.profile)
        self.assertIn("FINAL,Final", self.profile)
        self.assertIn("dns.alidns.com = 223.5.5.5", self.profile)
        self.assertIn("DOMAIN-SUFFIX,raw.githubusercontent.com,Proxy", self.profile)


if __name__ == "__main__":
    unittest.main()
