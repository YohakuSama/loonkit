#!/usr/bin/env python3
"""Run active checks on every change; full historical/beta checks separately."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
HISTORICAL = frozenset((
    "test_native_only_loom_trial.py", "test_release_promoted.py",
    "test_release_promotion_gate.py", "test_routing_candidate.py",
    "test_v702_candidate.py", "test_v703_formal.py",
))


def run(mode: str) -> bool:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    selected = []
    for path in sorted(TESTS.glob("test_*.py")):
        if mode == "current" and (path.name.startswith("test_beta_") or
                                   path.name in HISTORICAL):
            continue
        suite.addTests(loader.discover(str(TESTS), pattern=path.name))
        selected.append(path.name)
    if not selected:
        raise RuntimeError("no test modules selected")
    print("Test suite:", mode, "modules:", ", ".join(selected), flush=True)
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("current", "all"))
    args = parser.parse_args()
    sys.exit(0 if run(args.mode) else 1)
