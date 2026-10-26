#!/usr/bin/env python3
"""Offline source-update proposal and rule-level diff. Never publishes or locks.

The old consolidated upstream origins remain unrecoverable. A proposed new
source can ONLY become a future release after licensing, code review, explicit
manifest + lock updates and all release gates, never by invoking this tool.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/"build/sources.lock.json"


def review(source: str, proposed: Path, root: Path=ROOT) -> dict:
    manifest=json.loads((root/"build/sources.lock.json").read_text(encoding="utf-8"))
    sources={entry["path"]:entry for entry in manifest["inputs"]}
    if source not in sources or not source.startswith("rules/inputs/"):
        raise ValueError("only frozen composite-source proposals are supported")
    current=root/source
    if not current.is_file() or hashlib.sha256(current.read_bytes()).hexdigest()!=sources[source]["sha256"]:
        raise ValueError("current frozen input failed SHA256 verification")
    if proposed.resolve() == current.resolve():
        raise ValueError("use distinct proposed snapshot; do not rewrite immutable inputs")
    if proposed.resolve().is_relative_to((root/"rules/generated").resolve()) or proposed.resolve().is_relative_to((root/"rules/releases").resolve()):
        raise ValueError("cannot use a production output as upstream source")
    before=current.read_bytes()
    after=proposed.read_bytes()
    if not after or len(after)>50_000_000:
        raise ValueError("empty/oversized proposed input")
    old={x.strip() for x in before.decode("utf-8").splitlines()
         if x.strip() and not x.lstrip().startswith(("#",";","//"))}
    new={x.strip() for x in after.decode("utf-8").splitlines()
         if x.strip() and not x.lstrip().startswith(("#",";","//"))}
    if len(new)<1:
        raise ValueError("proposed input contains no rules")
    # Historic mixed input contains legacy matcher classes the compiler already
    # isolates. Validate only newly added entries through the *real compiler*
    # grammar, not a weaker comma-count check that could admit invalid ASN/IP.
    from rule_engine import normalize
    add=sorted(new-old)
    remove=sorted(old-new)
    for line in add:
        try:
            canonical=normalize(line)
        except (ValueError, TypeError) as exc:
            raise ValueError("invalid newly proposed Loon matcher: "+line[:120]) from exc
        if not canonical:
            raise ValueError("missing newly proposed Loon matcher: "+line[:120])
        if line.split(",",1)[0].upper()=="GEOIP":
            raise ValueError("unexpected GEOIP in locked composite input: "+line[:120])
    # Keep the complete, deterministic matcher-level change set, not merely
    # the first thirty examples. Every removed or added line is reviewable.
    # The digest protects the ordered change lists when exporting the report.
    change_set = {"added": add, "removed": remove}
    complete_delta = json.dumps(change_set, sort_keys=True, ensure_ascii=False,
                                separators=(",", ":")).encode("utf-8")
    risk_families = {"DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6", "IP-ASN"}
    high_risk = [line for line in add+remove
                 if line.split(",", 1)[0].upper() in risk_families]
    return {
        "schema_version":1, "status":"PENDING_REVIEW_NOT_PUBLISHED",
        "source_path":source, "historical_lineage":"NOT_RECOVERABLE_FROM_MERGED_SNAPSHOT",
        "original_source_sha256":hashlib.sha256(before).hexdigest(),
        "proposed_sha256":hashlib.sha256(after).hexdigest(),
        "added_rule_count":len(add), "removed_rule_count":len(remove),
        "old_distinct_matchers":len(old), "proposed_distinct_matchers":len(new),
        "added_by_kind":dict(sorted(Counter(x.split(",")[0] for x in add).items())),
        "removed_by_kind":dict(sorted(Counter(x.split(",")[0] for x in remove).items())),
        "added_sample":add[:30], "removed_sample":remove[:30],
        "full_change_set":change_set,
        "change_set_sha256":hashlib.sha256(complete_delta).hexdigest(),
        "high_risk_matcher_changes":len(high_risk),
        "risk_sample":high_risk[:30],
        "manual_legal_review":"REQUIRED",
        "manifest_and_source_lock_update":"REQUIRED_IN_REVIEWED_PR",
        "new_release_candidate_and_device_retest":"REQUIRED",
        "release_write_performed":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--proposed",type=Path,required=True)
    p.add_argument("--report",type=Path)
    a=p.parse_args()
    content=json.dumps(review(a.source,a.proposed),sort_keys=True,indent=2,ensure_ascii=False)+"\n"
    if a.report:
        # A review report is not allowed to overwrite source, compiler inputs,
        # published rules or critical metadata by supplying --report manually.
        target=a.report.resolve()
        protected=tuple((ROOT/p).resolve() for p in
                        ("rules","build","scripts","tests","release",".github","docs","icons","plugins","src"))
        if any(target.is_relative_to(p) for p in protected) or target in {
            (ROOT/"LoonKit.lcf").resolve(),(ROOT/"LoonKit.PrivacyDNS.lcf").resolve(),
            (ROOT/"build/release_manifest.json").resolve(),
            (ROOT/"build/legal_evidence.json").resolve(),
            (ROOT/"build/release_spec.json").resolve(),
        }:
            raise ValueError("review report cannot overwrite locked sources or release artifacts")
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(content,encoding="utf-8")
    else:
        print(content,end="")


if __name__=="__main__": main()
