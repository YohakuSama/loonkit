"""v7.0.4 service policy and local-route regression coverage."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from release_v704 import check, render, LOCAL_TRAE, DIRECT_GROUPS
from audit_upstream_703 import owner
from audit_v702 import lines


class RoutingV704Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = (ROOT / "LoonKit.lcf").read_bytes()
        cls.previous = (ROOT / "build/candidates/v7.0.3/LoonKit.lcf").read_bytes()
        cls.manifest = json.loads((ROOT / "build/release_manifest.json").read_text())

    def test_exact_reviewed_runtime_diff(self):
        self.assertEqual(self.current, render(self.previous))
        self.assertEqual(self.current.decode().splitlines()[0], "# LoonKit v7.0.4")
        self.assertEqual(len(DIRECT_GROUPS), 5)

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
        result = check(root=ROOT)
        self.assertEqual(result["version"], "v7.0.4")
        self.assertEqual(result["remote_subscriptions"], 43)
        self.assertEqual(result["strategy_groups"], 39)
        self.assertEqual(result["remote_matchers"], 196565)


if __name__ == "__main__":
    unittest.main()
