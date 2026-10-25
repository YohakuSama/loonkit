#!/usr/bin/env python3
"""Stage REAL changed upstream rule assets for beta review, never for implicit publication.

Reuses the existing 87-source parser, immutable baseline and complete risk audit.
Failing/stale/empty sources are never interpreted as authorized removals.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import upstream_review

VERSIONS = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+-beta\.[1-9][0-9]*\Z")
DIRECT_GROUPS = frozenset(("ChinaDirect", "DomesticCore", "SteamCN", "AppleOTA"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stage(report: dict, snapshots: dict[str, bytes], review_data: dict,
          destination: Path, version: str, root: Path = ROOT) -> dict:
    """Generate actual proposed assets plus evidence; caller must explicitly review/pin."""
    if not VERSIONS.fullmatch(version):
        raise ValueError("version must be explicit vX.Y.Z-beta.N")
    out = destination.resolve()
    repo = root.resolve()
    if out == repo or out.is_relative_to(repo) or repo.is_relative_to(out):
        raise ValueError("stage outside the checkout; never modify production or beta")
    if destination.is_symlink() or (out.exists() and any(out.iterdir())):
        raise ValueError("output destination must be empty and not a symlink")
    old = review_data["rules"]
    proposals = review_data["unapproved_proposals"]
    if set(old) != set(proposals) or set(old) != set(report["groups"]):
        raise ValueError("missing proposed or baseline rule group")
    records = report.get("sources", [])
    source_ids = {r["id"] for r in records}
    if len(source_ids) != report["source_count"] or len(source_ids) != len(records):
        raise ValueError("source manifest incomplete or has duplicates")
    global_incomplete = bool(report["incomplete_sources"] or report["incomplete_groups"]
                             or len(snapshots) != report["snapshot_count"])
    if not out.exists():
        out.mkdir(parents=True)
    evidence = out / "evidence"
    upstream_review.write_review(evidence, report, snapshots, review_data, root=root)
    staged_groups = {}
    for group in sorted(old):
        before, after = old[group], proposals[group]
        if not before:
            raise ValueError("missing last-known-good baseline group: " + group)
        if not isinstance(after, (set, frozenset)):
            raise ValueError("source parser returned unexpected proposal data")
        changed = before != after
        removed = sorted(before - after)
        added = sorted(after - before)
        risk = report["groups"][group]
        flags = review_data.get("full_risk_audit", {}).get(group, {})
        elevated = (bool(removed) or group in DIRECT_GROUPS and changed
                    or risk.get("volume_change_percent", 0) > 20
                    or any(entry.get("review_tier") == "ELEVATED"
                           for entry in flags.get("additions", [])))
        # Failure retains the last valid baseline rather than emitting an empty
        # ruleset or pretending that a partial upstream result is a deletion.
        invalid = global_incomplete or group in report["incomplete_groups"] or not after
        actual = before if invalid else after
        name = "AnimeCrazy" if group == "動畫瘋" else group
        path = "proposed-assets/rules/releases/" + version + "/" + name + ".list"
        body = ("# PROPOSAL ONLY; NOT SAFE TO PUBLISH WITHOUT REVIEW\n"
                + "\n".join(sorted(actual)) + "\n").encode("utf-8")
        dest = out / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        staged_groups[group] = {
            "path": path, "sha256": sha(body),
            "baseline_count": len(before), "fetched_count": len(after),
            "staged_count": len(actual), "added": len(added), "removed": len(removed),
            "status": "RETAINED_LAST_GOOD_ON_INCOMPLETE_SOURCE" if invalid else (
                "HIGH_RISK_HUMAN_REVIEW" if elevated else (
                    "ROUTINE_CANDIDATE_REVIEW" if changed else "UNCHANGED")),
            "risk_categories": risk.get("risk_categories", {}),
            "requires_explicit_approval": bool(changed),
        }
    complete = not global_incomplete
    result = {
        "schema_version": 1, "version": version,
        "status": "REVIEW_ONLY_UNPINNED_NOT_IMPORTABLE",
        "publication_allowed": False,
        "branch_push_allowed": False,
        "global_source_integrity_complete": complete,
        "source_count": report["source_count"],
        "source_snapshots": [
            {key: row.get(key) for key in ("id", "group", "url", "status", "sha256", "bytes",
                "fetched_at_utc", "http_etag", "http_last_modified", "expanded_includes")}
            for row in records],
        "groups": staged_groups,
        "baseline_commit": report.get("baseline_commit"),
        "runtime_baseline": report.get("runtime_baseline") is True,
        "must_pin_assets_in_reviewed_git_commit": True,
        "do_not_replace_any_published_resource": True,
        "requires_staged_diff_acceptance": True,
        "full_diff_sha256": report["full_delta_sha256"],
    }
    (out / "BETA_UPSTREAM_MANIFEST.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return result


def run(version: str, destination: Path, root: Path = ROOT) -> dict:
    # Compare against the actual beta, including its seven supplementary
    # service owners. Never reintroduce the old formal CN/UA/ad-filter policy.
    import beta_channel
    beta_channel.validate(root)
    meta = json.loads((root / "build/beta_manifest.json").read_text())
    baseline = upstream_review.runtime_baseline(root,profile_path='beta/LoonKit.lcf',manifest_path='build/beta_manifest.json')
    # Generated routine overlays are members of source_group_tags and have
    # already been included once in their existing service baseline.
    report, snapshots, data = upstream_review.build_report(root=root, baseline_rules=baseline)
    report["runtime_baseline"] = True
    report["baseline_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    return stage(report, snapshots, data, destination, version, root=root)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    summary = run(args.version, args.output)
    print(json.dumps({
        "status": summary["status"],
        "global_source_integrity_complete": summary["global_source_integrity_complete"],
        "proposed_policy_groups": len(summary["groups"]),
        "publication_allowed": summary["publication_allowed"]
    }, sort_keys=True))
