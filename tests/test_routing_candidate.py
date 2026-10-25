"""Unified routing candidate must preserve the existing effective rule inventory."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from routing_candidate_audit import audit

class RoutingCandidateAuditTests(unittest.TestCase):
    def test_pinned_candidate_matches_v700_runtime(self):
        result = audit()
        self.assertEqual(result["resource_count"], 36)
        self.assertEqual(result["matcher_count"], 196486)
        self.assertEqual(result["candidate"], "v7.0.1")
        self.assertEqual(result["invariant"], "identical rule bytes, policy and subscription order")

if __name__ == "__main__":
    unittest.main()
