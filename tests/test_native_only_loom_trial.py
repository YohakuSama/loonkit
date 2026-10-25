"""Guard experimental native-only Loon rule alternative (NOT routing-equivalent).

The six source assets use geoIP composite logic and reportedly trigger a VPN
extension restart when matched on user hardware. Here none of those composite
expressions may enter the new assets. This does NOT prove runtime stability,
absence of DNS leaks, or preservation of CN-versus-overseas routing.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("RegionalCN", "AppleOTA", "Bilibili", "Microsoft", "Apple", "Paypal")
SRC = ROOT / "rules/releases/v6.5.8"
TRIAL_DIR = ROOT / "rules/experiments/v6.5.8-native-no-composite"
PIN = "47c8efee053f1f36acbd4431d8c1d1ad92532d75"
CNT = {"RegionalCN": (2553, 1), "AppleOTA": (82, 82),
       "Bilibili": (128, 120), "Microsoft": (645, 645),
       "Apple": (1574, 1561), "Paypal": (246, 246)}
AND = re.compile(
    r"^AND,\(\(((?:DOMAIN|DOMAIN-SUFFIX|IP-CIDR|IP-CIDR6|IP-ASN),[^()]+)\),"
    r"\((GEOIP,CN|NOT,\(\(GEOIP,CN\)\))\)\)$"
)
DOMAIN = re.compile(r"^DOMAIN(?:-SUFFIX)?,[^(),\s]+$")
GEOIP = "GEOIP,CN,no-resolve"


def data(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def rules(text: str) -> list[str]:
    return [line for line in text.splitlines()
            if line and not line.lstrip().startswith("#")]


def remote(text: str) -> list[str]:
    return [line for line in text.split("[Remote Rule]\n", 1)[1]
            .split("\n[", 1)[0].splitlines() if line.startswith("https://")]


def tag(line: str) -> str:
    m = re.search(r"(?:^|,)\s*tag=([^,]+)", line)
    if not m:
        raise ValueError("missing tag")
    return m.group(1)


class TestNativeOnlyLoonTrial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = data(ROOT / "LoonKit.lcf")
        cls.trial = data(ROOT / "LoonKit.NativeRulesTrial.lcf")

    def test_all_six_resources_rewrite_as_noncomposite(self):
        for name in NAMES:
            original = rules(data(SRC / f"{name}.list"))
            rewritten = rules(data(TRIAL_DIR / f"{name}.list"))
            self.assertEqual((len(original), len(rewritten)), CNT[name], name)
            source_children = []
            for line in original:
                m = AND.fullmatch(line)
                self.assertIsNotNone(m, name + ": " + line[:100])
                if name == "RegionalCN":
                    self.assertEqual(m.group(2), "GEOIP,CN")
                else:
                    self.assertEqual(m.group(2), "NOT,((GEOIP,CN))")
                source_children.append(m.group(1))
            if name == "RegionalCN":
                self.assertEqual(rewritten, [GEOIP])
            else:
                expected_domains = [
                    child for child in source_children
                    if child.startswith(("DOMAIN,", "DOMAIN-SUFFIX,"))
                ]
                self.assertEqual(rewritten, expected_domains)
                self.assertTrue(all(DOMAIN.fullmatch(row) for row in rewritten))
            self.assertFalse(any(
                "AND," in line or "NOT," in line or "OR," in line
                for line in rewritten
            ), name)

    def test_trial_preserves_all_six_subscription_tags_and_policies(self):
        before, after = remote(self.original), remote(self.trial)
        self.assertEqual(len(before), 37)
        self.assertEqual(len(after), 37)
        self.assertEqual([tag(x) for x in before], [tag(x) for x in after])
        changed = []
        for old, new in zip(before, after):
            t = tag(old)
            self.assertEqual(old.split(",", 1)[1], new.split(",", 1)[1])
            if t.startswith("Our-") and t.removeprefix("Our-") in NAMES:
                name = t.removeprefix("Our-")
                expected = (
                    "https://raw.githubusercontent.com/YohakuSama/loonkit/"
                    + PIN + f"/rules/experiments/v6.5.8-native-no-composite/{name}.list"
                )
                self.assertEqual(new.split(",", 1)[0], expected)
                self.assertTrue(new.endswith("enabled=true"))
                changed.append(name)
            else:
                self.assertEqual(old, new)
        self.assertEqual(set(changed), set(NAMES))

    def test_profile_unchanged_except_six_remote_asset_urls_and_comments(self):
        before_urls = set(remote(self.original))
        after_urls = set(remote(self.trial))
        without = lambda text, urls: [
            line for line in text.splitlines()
            if line.strip() and not line.startswith("#") and line not in urls
        ]
        self.assertEqual(
            without(self.original, before_urls),
            without(self.trial, after_urls)
        )
        self.assertIn(
            "\nGEOIP,CN,DIRECT,no-resolve\nFINAL,Final\n",
            self.trial
        )
        self.assertIn("doh-server = https://dns.alidns.com/dns-query",
                      self.trial)
        self.assertIn("dns-server = 223.5.5.5,223.6.6.6", self.trial)


if __name__ == "__main__":
    unittest.main()
