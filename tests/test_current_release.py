"""Active production route and manifest regression coverage."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from release_engine import check, render
from audit_upstream_703 import owner
from audit_v702 import lines

LOCAL_TRAE = ("DOMAIN,trae-api-sg.mchost.guru,AI", "DOMAIN,trae-api-us.mchost.guru,AI")
DIRECT_GROUPS = ("Apple", "Microsoft", "Bilibili", "Speedtest", "Line")


class CurrentRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = (ROOT / "LoonKit.lcf").read_bytes()
        cls.manifest = json.loads((ROOT / "build/release_manifest.json").read_text())

    def test_exact_reviewed_runtime_diff(self):
        self.assertEqual(self.current, render(ROOT))
        self.assertEqual(self.current.decode().splitlines()[0], "# LoonKit " + json.loads((ROOT / "build/release_spec.json").read_text())["stable_release_version"])
        group_section = self.current.decode().split("[Proxy Group]\n", 1)[1].split("\n[", 1)[0]
        for group in DIRECT_GROUPS:
            if any(line.startswith(group + " =") for line in group_section.splitlines()):
                self.assertIn(group + " = select,DIRECT,Proxy,Auto,Fallback,ALL_Filter,", group_section)

    def test_trae_routing_not_taken_by_tiktok_or_cn(self):
        rows = self.manifest["runtime_resources"]
        remote = {row["path"]: lines((ROOT / row["path"]).read_bytes()) for row in rows}
        local = [x.strip() for x in self.current.decode().split("[Rule]\n", 1)[1].split("\n[", 1)[0].splitlines() if x.strip()]
        for line in LOCAL_TRAE:
            if line in local:
                self.assertEqual(owner(line.split(",")[1], remote, rows, local), "AI")
        if any("trae.ai" in line for line in local):
            self.assertEqual(owner("trae.ai", remote, rows, local), "AI")
        self.assertEqual(owner("tiktok.com", remote, rows, local), "TikTok")
        self.assertEqual(owner("raw.githubusercontent.com", remote, rows, local), "Proxy")
        for line in LOCAL_TRAE:
            self.assertLessEqual(local.count(line), 1)

    def test_checksum_and_immutable_resources(self):
        result = check(ROOT)
        group_section = self.current.decode().split("[Proxy Group]\n", 1)[1].split("\n[", 1)[0]
        self.assertEqual(result["version"], json.loads((ROOT / "build/release_spec.json").read_text())["stable_release_version"])
        self.assertEqual(result["resources"], self.manifest["remote_subscription_count"])
        self.assertEqual(result["groups"], len([line for line in group_section.splitlines() if line.strip() and not line.lstrip().startswith("#")]))
        self.assertEqual(result["matchers"], self.manifest["remote_rule_count"])


if __name__ == "__main__":
    unittest.main()
