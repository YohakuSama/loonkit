#!/usr/bin/env python3
"""Deterministic, read-only-by-default builder for the v6.5.8 no-resolve experiment.

Never writes formal release assets. Avoids changing DNS, service policies, matchers
or historical checksums. Usage:
  python3 scripts/build_geoip_no_resolve_trial.py --check
  python3 scripts/build_geoip_no_resolve_trial.py --write
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("RegionalCN", "AppleOTA", "Bilibili", "Microsoft", "Apple", "Paypal")
SOURCE = ROOT / "rules/releases/v6.5.8"
TARGET = ROOT / "rules/experiments/v6.5.8-geoip-no-resolve"

PATTERN = re.compile(
    r"AND,\(\(((?:DOMAIN|DOMAIN-SUFFIX|IP-CIDR|IP-CIDR6|IP-ASN),[^()]+)\),"
    r"\((?:GEOIP,CN|NOT,\(\(GEOIP,CN\)\))\)\)"
)


def render(name: str) -> str:
    """Preserve matcher and all ordering; only add no-resolve to inner GEOIP."""
    if name not in NAMES:
        raise ValueError(f"unknown experimental source: {name}")
    original = (SOURCE / f"{name}.list").read_text(encoding="utf-8")
    records = [row for row in original.splitlines()
               if row.strip() and not row.lstrip().startswith("#")]
    if not records or any(PATTERN.fullmatch(row) is None for row in records):
        raise ValueError(f"{name}: original shape is not known; refuse rewrite")
    transformed = [row.replace("GEOIP,CN", "GEOIP,CN,no-resolve") for row in records]
    if any(row.count("GEOIP,CN,no-resolve") != 1 for row in transformed):
        raise ValueError(f"{name}: failed to rewrite exactly one inner GEOIP")
    header = (
        f"# LoonKit v6.5.8 {name} - GEOIP child no-resolve device experiment\n"
        "# Same domain/IP child matchers and order as original; GEOIP,CN now uses no-resolve.\n"
        "# CAUTION: does not auto-resolve hostnames, so policy outcomes can differ for unresolved domains.\n"
    )
    return header + "\n".join(transformed) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="reject stale or modified assets")
    mode.add_argument("--write", action="store_true", help="rewrite experiment files only")
    args = parser.parse_args()
    for name in NAMES:
        target = TARGET / f"{name}.list"
        rendered = render(name)
        if args.write:
            if not target.parent.exists():
                raise RuntimeError("experiment target path missing; never create release folders")
            target.write_text(rendered, encoding="utf-8")
        elif not target.is_file() or target.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"stale experiment resource: {target.relative_to(ROOT)}")
    print(f"OK: {len(NAMES)} non-production no-resolve experiment assets")


if __name__ == "__main__":
    main()
