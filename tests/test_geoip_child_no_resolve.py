"""No-resolve-only six-subscription test: never modify published v6.5.8 or DNS."""
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("RegionalCN", "AppleOTA", "Bilibili", "Microsoft", "Apple", "Paypal")
PIN = "2301e7ca3986afe78078cb95971701c67ee0b674"
PREFIX = "rules/experiments/v6.5.8-geoip-no-resolve/"
GEOIP = "GEOIP,CN,DIRECT,no-resolve"
FINAL = "FINAL,Final"


def records(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("AND,")]


def config(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def remotes(text: str) -> list[str]:
    return [line for line in text.split("[Remote Rule]\n", 1)[1]
            .split("\n[", 1)[0].splitlines() if line.startswith("https://")]


def tag(line: str) -> str:
    match = re.search(r"(?:^|,)\s*tag=([^,]+)", line)
    if not match:
        raise AssertionError("remote entry without tag")
    return match.group(1)


def directives(text: str) -> list[str]:
    return [line for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")]


class TestNoResolveGeoIPChildren(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = config("LoonKit.lcf")
        cls.candidate = config("LoonKit.GeoIPNoResolve.lcf")

    def test_experimental_source_builder_is_reproducible(self):
        check = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_geoip_no_resolve_trial.py"),
             "--check"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn("6 non-production no-resolve experiment assets",
                      check.stdout)

    def test_six_original_matchers_preserved_and_only_geoip_flag_added(self):
        total = 0
        for name in NAMES:
            original = records(ROOT / f"rules/releases/v6.5.8/{name}.list")
            changed = records(ROOT / PREFIX / f"{name}.list")
            self.assertEqual(len(original), len(changed), name)
            self.assertEqual(
                [line.replace("GEOIP,CN,no-resolve", "GEOIP,CN")
                 for line in changed], original, name,
            )
            for line in changed:
                self.assertEqual(line.count("GEOIP,CN,no-resolve"), 1, line)
                self.assertTrue(line.startswith("AND,(("), line)
            total += len(original)
        self.assertEqual(total, 5228)

    def test_only_six_subscription_urls_differ(self):
        original = remotes(self.original)
        candidate = remotes(self.candidate)
        self.assertEqual(len(original), 37)
        self.assertEqual(len(candidate), 37)
        self.assertEqual([tag(x) for x in original],
                         [tag(x) for x in candidate])
        rewritten = 0
        for a, b in zip(original, candidate):
            name = tag(a).removeprefix("Our-")
            if name in NAMES:
                self.assertEqual(
                    b.split(",", 1)[0],
                    "https://raw.githubusercontent.com/YohakuSama/loonkit/"
                    + PIN + "/" + PREFIX + name + ".list",
                )
                self.assertEqual(a.split(",", 1)[1], b.split(",", 1)[1])
                self.assertIn("enabled=true", b)
                rewritten += 1
            else:
                self.assertEqual(a, b)
        self.assertEqual(rewritten, 6)

    def test_dns_policy_geoip_fallback_and_all_other_sections_identical(self):
        a = directives(self.original)
        b = directives(self.candidate)
        orig_urls = {line for line in remotes(self.original)}
        cand_urls = {line for line in remotes(self.candidate)}
        self.assertEqual([line for line in a if line not in orig_urls],
                         [line for line in b if line not in cand_urls])
        self.assertEqual(
            directives(self.candidate.split("[Rule]\n")[1].split("\n[")[0])[-2:],
            [GEOIP, FINAL],
        )
        self.assertEqual(
            self.original.split("[General]\n", 1)[1].split("\n[", 1)[0],
            self.candidate.split("[General]\n", 1)[1].split("\n[", 1)[0],
        )


if __name__ == "__main__":
    unittest.main()
