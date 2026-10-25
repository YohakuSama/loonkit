"""Regression checks for v7.0.2 candidate service policies and LSR sources."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import audit_v702

class V702CandidateTests(unittest.TestCase):
    def test_pinned_lsr_resources_and_policy_ownership(self):
        result = audit_v702.check()
        self.assertEqual(result["policy_groups"],39)
        self.assertEqual(result["rule_sets"],42)
        self.assertEqual(result["icons"],40)
        self.assertEqual(result["ownership_cases"],17)

if __name__ == "__main__":
    unittest.main()
