#!/usr/bin/env python3
"""Evaluate completeness of the read-only upstream review, not release approval."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path


def assess(report: dict, source_catalog: dict) -> dict:
    entries = source_catalog["sources"]
    expected_ids = [entry["id"] for entry in entries]
    seen = report.get("sources", [])
    observed_ids = [entry.get("id") for entry in seen]
    problems = []
    if len(expected_ids) != len(set(expected_ids)):
        problems.append("Duplicate source IDs in source catalog")
    if len(observed_ids) != len(set(observed_ids)):
        problems.append("Duplicate source IDs in review result")
    missing = sorted(set(expected_ids) - set(observed_ids))
    unexpected = sorted(set(observed_ids) - set(expected_ids))
    if missing:
        problems.append("Missing source IDs: " + ", ".join(missing))
    if unexpected:
        problems.append("Unexpected source IDs: " + ", ".join(unexpected))
    count = len(expected_ids)
    if report.get("source_count") != count:
        problems.append(f"Catalog count mismatch: {report.get('source_count')} vs {count}")
    if report.get("snapshot_count") != count:
        problems.append(f"Raw snapshots incomplete: {report.get('snapshot_count')} vs {count}")
    excluded_total = 0
    sources_with_exclusions = 0
    for entry in seen:
        sid = entry.get("id", "<missing>")
        status = entry.get("status")
        if status not in {"PARSED_FOR_REVIEW", "PARSED_WITH_DOCUMENTED_EXCLUSIONS"}:
            problems.append(f"{sid}: {status or 'missing status'}")
        excluded = entry.get("excluded_expressions", [])
        if not isinstance(excluded, list):
            problems.append(f"{sid}: exclusions are not a list")
            excluded = []
        if entry.get("excluded_count", 0) != len(excluded):
            problems.append(f"{sid}: excluded expression count does not match evidence")
        if (status == "PARSED_WITH_DOCUMENTED_EXCLUSIONS") != bool(excluded):
            problems.append(f"{sid}: excluded status mismatches expression records")
        if excluded:
            sources_with_exclusions += 1
        excluded_total += len(excluded)
        for item in excluded:
            reasons = {"URL-REGEX": "MITM_URL_REGEX_NOT_DOMAIN_RULE",
                       "regexp": "HOST_REGEX_CANNOT_SAFELY_WIDEN_TO_SUFFIX"}
            kind = item.get("kind")
            expression = item.get("expression")
            claimed_hash = item.get("sha256")
            if (kind not in reasons
                    or item.get("reason") != reasons.get(kind)
                    or not isinstance(item.get("line"), int) or item["line"] < 1
                    or not isinstance(expression, str) or not expression.strip()
                    or not re.fullmatch(r"[0-9a-f]{64}", str(claimed_hash or ""))
                    or (isinstance(expression, str)
                        and claimed_hash != hashlib.sha256(
                            expression.encode("utf-8")).hexdigest())):
                problems.append(f"{sid}: unsupported exclusion evidence is malformed")
        if entry.get("invalid_count", 0) != 0:
            problems.append(f"{sid}: {entry.get('invalid_count')} unknown/unparsed lines")
        if entry.get("minimum_satisfied") is not True:
            problems.append(f"{sid}: minimum source size not met or unchecked")
        if not entry.get("sha256"):
            problems.append(f"{sid}: missing content hash")
    if report.get("excluded_expressions", 0) != excluded_total:
        problems.append("Declared excluded expression count mismatch")
    if report.get("sources_with_exclusions", 0) != sources_with_exclusions:
        problems.append("Declared excluded source count mismatch")
    if report.get("incomplete_sources") != 0:
        problems.append(f"Declared incomplete source count: {report.get('incomplete_sources')}")
    if report.get("incomplete_groups"):
        problems.append("Incomplete groups: " + ", ".join(report["incomplete_groups"]))
    if report.get("publication_allowed") is not False:
        problems.append("Unapproved rule publication guard missing")
    return {"coverage_complete": not problems,
            "translation_complete": not problems and excluded_total == 0,
            "excluded_expressions": excluded_total,
            "sources_with_exclusions": sources_with_exclusions,
            "included_snapshot_count": report.get("included_snapshot_count", 0),
            "checked": len(seen),
            "expected": count, "snapshot_count": report.get("snapshot_count"),
            "problems": problems}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--catalog", type=Path, default=Path("rules/sources.json"))
    args = p.parse_args()
    if not args.report.is_file():
        print("INCOMPLETE: no upstream review report generated.")
        return 1
    result = assess(json.loads(args.report.read_text(encoding="utf-8")),
                    json.loads(args.catalog.read_text(encoding="utf-8")))
    excluded = report.get("runtime_groups_not_in_legacy_catalog", [])
    summary = ("## Legacy 87-source coverage (not release approval)\\n"
               f"- Current owners outside catalog: {', '.join(excluded) if excluded else 'none'}\\n"

               f"- Reviewed: {result['checked']}/{result['expected']}\n"
               f"- Raw snapshots: {result['snapshot_count']}/{result['expected']}\n"
               f"- All source lines classified: {'YES' if result['coverage_complete'] else 'NO'}\n"
               f"- All rules safely translated: {'YES' if result['translation_complete'] else 'NO'}\n"
               f"- Documented regex exclusions: {result['excluded_expressions']} "
               f"across {result['sources_with_exclusions']} catalog sources\n"
               f"- Nested include snapshots: {result['included_snapshot_count']}\n"
               "- Exclusions are NOT included in candidate matchers.\n"
               "- Published rules unchanged; release is NOT approved.\n")
    for item in result["problems"]:
        summary += f"- Issue: {item}\n"
    print(summary)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fd:
            fd.write(summary)
    return 0 if result["coverage_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
