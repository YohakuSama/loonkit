"""Current stable route regression coverage via the generic release engine."""
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


class RoutingV704Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = (ROOT / "LoonKit.lcf").read_bytes()
        cls.manifest = json.loads((ROOT / "build/release_manifest.json").read_text())

    def test_exact_reviewed_runtime_diff(self):
        self.assertEqual(self.current, render(ROOT))
        self.assertEqual(self.current.decode().splitlines()[0], "# LoonKit " + json.loads((ROOT / "build/release_spec.json").read_text())["stable_release_version"])
        group_section = self.current.decode().split("[Proxy Group]\n", 1)[1].split("\n[", 1)[0]
        for group in DIRECT_GROUPS:
            self.assertIn(group + " = select,DIRECT,Proxy,Auto,Fallback,ALL_Filter,", group_section)

    def test_trae_routing_not_taken_by_tiktok_or_cn(self):
        rows = self.manifest["runtime_resources"]
        remote = {row["path"]: lines((ROOT / row["path"]).read_bytes()) for row in rows}
        local = [x.strip() for x in self.current.decode().split("[Rule]\n", 1)[1].split("\n[", 1)[0].splitlines() if x.strip()]
        for host in ("trae-api-sg.mchost.guru", "trae-api-us.mchost.guru", "trae.ai"):
            self.assertEqual(owner(host, remote, rows, local), "AI")
        self.assertEqual(owner("tiktok.com", remote, rows, local), "TikTok")
        self.assertEqual(owner("raw.githubusercontent.com", remote, rows, local), "Proxy")
        for line in LOCAL_TRAE:
            self.assertEqual(local.count(line), 1)

    def test_checksum_and_immutable_resources(self):
        result = check(ROOT)
        self.assertEqual(result["version"], json.loads((ROOT / "build/release_spec.json").read_text())["stable_release_version"])
        self.assertEqual(result["resources"], 43)
        self.assertEqual(result["groups"], 39)
        self.assertEqual(result["matchers"], 196565)


if __name__ == "__main__":
    unittest.main()
