"""Check the frozen v7.0.3 snapshot independently of the current v7.0.4 profile."""
from pathlib import Path
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from reviewed_release import validate_records

class V703FormalTests(unittest.TestCase):
    def test_frozen_native_service_routes(self):
        previous = (ROOT / "build/candidates/v7.0.3/LoonKit.lcf").read_bytes()
        meta = json.loads((ROOT / "build/candidates/v7.0.3/candidate_manifest.json").read_text())
        self.assertEqual(meta["version"], "v7.0.3")
        self.assertEqual(hashlib.sha256(previous).hexdigest(), meta["profile_sha256"])
        self.assertEqual(len(meta["rule_sets"]), 43)
        checked = validate_records(previous, meta["rule_sets"], ROOT)
        self.assertEqual(len(checked), 43)
        self.assertGreater(sum(x["matcher_count"] for x in checked), 196400)
        self.assertTrue(meta["asset_commit"])

if __name__ == "__main__":
    unittest.main()
