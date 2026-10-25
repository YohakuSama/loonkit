"""Verify the current v7.0.3 immutable formal release and preserved rollback."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import release_v703

class V703FormalTests(unittest.TestCase):
    def test_frozen_native_service_routes(self):
        x=release_v703.check()
        self.assertEqual(x["version"],"v7.0.3")
        self.assertEqual(x["strategy_groups"],39)
        self.assertEqual(x["rule_sets"],43)
        self.assertEqual(x["icon_files"],40)
        self.assertTrue(x["asset_commit"])
        self.assertGreater(x["matchers"],196400)

if __name__=="__main__":
    unittest.main()
