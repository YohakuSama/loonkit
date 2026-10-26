#!/usr/bin/env python3
"""Read-only formal release verification entry point."""
import argparse
import json
from release_checksums import check_public_checksums


def verify(remote=False):
    from release_engine import check
    return check(remote=remote)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.add_argument("--remote", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.remote), sort_keys=True))
