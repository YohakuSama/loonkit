#!/usr/bin/env python3
"""Check real upstream license bytes, third-party notices, and independent review.

This verifies preservation and review evidence, NOT underlying legal rights.
An asserted legal clearance requires a human-reviewed decision scoped to the
exact frozen candidate. Incomplete provenance cannot be auto-waived.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
BASE="build/"
SHA256=re.compile(r"[0-9a-f]{64}\Z")
GIT_SHA=re.compile(r"[0-9a-f]{40}\Z")
FAMILIES={
 "blackmatrix7":("GPL-2.0-only","rules/LICENSE.GPL-2.0",
                 "d159169d1050894d3ea3b98e1c965c4058208fe1"),
 "v2fly":("MIT","rules/LICENSE.MIT-V2FLY",
          "1f086538ba3a1d26f46ec44cfda12c2a0c4753a6"),
 "felixonmars":("WTFPL-2.0","rules/LICENSE.WTFPL-FELIXONMARS",
                "e1d98509456e841f4cd793b21f14aac2c370f9e9"),
}
REVIEW_TOPICS=(
 "merged_rule_redistribution",
 "gpl_and_copyleft_compliance",
 "blackmatrix7_special_statements",
 "original_provenance_gaps",
 "icon_trademark_rights",
 "plugin_script_rights",
)


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()


def review_artifact(root: Path, entry: dict, frozen_sha: str) -> None:
    if not isinstance(entry,dict) or entry.get("decision")!="APPROVED_AFTER_INDEPENDENT_REVIEW":
        raise ValueError("legal approval requires a substantive independent decision")
    reviewer=entry.get("reviewer")
    if not isinstance(reviewer,str) or len(reviewer.strip())<4 or reviewer.lower() in {"unknown","ai","automated"}:
        raise ValueError("missing accountable independent rights reviewer")
    stamp=entry.get("reviewed_at")
    try:
        dt=datetime.fromisoformat(stamp.replace("Z","+00:00"))
        if not dt.tzinfo:
            raise ValueError("review time needs timezone")
    except (AttributeError, ValueError) as exc:
        raise ValueError("review approval must have an actual timezone-aware date") from exc
    if entry.get("reviewed_commit")!=frozen_sha:
        raise ValueError("license review does not apply to this exact immutable rule commit")
    doc=entry.get("decision_document")
    if not isinstance(doc,str) or not re.fullmatch(r"build/legal-reviews/[A-Za-z0-9_.-]+\.json",doc):
        raise ValueError("legal review document must be a scoped JSON artifact under legal-reviews")
    path=root/doc
    if not path.is_file():
        raise ValueError("approved legal review has no committed decision evidence")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if entry.get("decision_sha256")!=digest:
        raise ValueError("legal review document checksum does not match")
    decision=json.loads(path.read_text(encoding="utf-8"))
    if decision.get("candidate_rule_commit")!=frozen_sha or decision.get("reviewer")!=reviewer:
        raise ValueError("legal report does not bind reviewed candidate and reviewer")
    if decision.get("decision")!="APPROVED_AFTER_INDEPENDENT_REVIEW":
        raise ValueError("legal report is not an affirmative decision")
    topics=decision.get("findings")
    if not isinstance(topics,dict) or set(topics)!=set(REVIEW_TOPICS):
        raise ValueError("independent review missing mandatory rights analyses")
    for topic in REVIEW_TOPICS:
        value=topics[topic]
        if not isinstance(value,dict) or value.get("status")!="CLEARED_WITH_BASIS":
            raise ValueError("uncleared legal topic: "+topic)
        if not isinstance(value.get("reasoning"),str) or len(value["reasoning"].strip())<80:
            raise ValueError("legal topic needs substantive reason and evidence: "+topic)
        if not isinstance(value.get("sources"),list) or not value["sources"]:
            raise ValueError("legal topic requires referenced source evidence: "+topic)


def check(root: Path=ROOT) -> dict:
    evidence=json.loads((root/BASE/"legal_evidence.json").read_text(encoding="utf-8"))
    if evidence.get("schema_version")!=1 or evidence.get("release_candidate")!="vNext-RC2":
        raise ValueError("unknown legal evidence version")
    # This evidence describes a historical merged snapshot, independently of
    # today's runtime inventory. Keep the reviewed scope bound to its bytes.
    relative=evidence.get("candidate_manifest_path", "")
    if not re.fullmatch(r"build/baselines/v[0-9]+\.[0-9]+\.[0-9]+/release_manifest\.json", relative):
        raise ValueError("historical evidence requires a scoped baseline manifest")
    raw=(root/relative).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=evidence.get("candidate_manifest_sha256"):
        raise ValueError("historical evidence manifest bytes changed")
    manifest=json.loads(raw)
    sha=manifest["source_snapshot_commit"]
    if not GIT_SHA.fullmatch(sha) or evidence.get("candidate_rule_commit")!=sha:
        raise ValueError("legal evidence does not match RC2 pinned Git commit")
    known={x["family"]:x for x in evidence.get("license_texts",[])}
    if set(known)!=set(FAMILIES):
        raise ValueError("missing upstream license text evidence")
    for family,(spdx,filename,blob) in FAMILIES.items():
        x=known[family]
        if (x.get("spdx"),x.get("local_path"),x.get("git_blob_sha1"))!=(spdx,filename,blob):
            raise ValueError("incorrect SPDX or source license record: "+family)
        if git_blob((root/filename).read_bytes())!=blob:
            raise ValueError("third-party license body changed: "+filename)
    notice=(root/BASE/"../docs/THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    for family in FAMILIES:
        if family not in notice or FAMILIES[family][0] not in notice:
            raise ValueError("public third party NOTICE is incomplete: "+family)
    catalog=json.loads((root/"rules/sources.json").read_text(encoding="utf-8"))["sources"]
    if len(catalog)!=87 or evidence.get("historical_source_inventory")!=BASE+"license_sources.json":
        raise ValueError("historical catalog is not fully declared")
    ledger=json.loads((root/BASE/"license_sources.json").read_text(encoding="utf-8"))
    if len(ledger.get("entries",[]))!=len(catalog):
        raise ValueError("historical ledger not complete")
    if evidence.get("blackmatrix7_readme",{}).get("git_blob_sha1")!="ca61b7558a2d500716265e0c3ae076e77ed82524":
        raise ValueError("separate upstream special notice not preserved")
    clear=evidence.get("clearance",{})
    if clear.get("status")=="NOT_EXECUTED" and evidence.get("status")=="NOT_INDEPENDENTLY_REVIEWED":
        return {"license_artifacts":"VERIFIED_PRESERVED", "independent_clearance":"NOT_EXECUTED",
                "redistribution_rights":"NOT_ATTESTED","upstream_families":3,
                "historical_sources":len(catalog)}
    if clear.get("status")!="APPROVED_AFTER_INDEPENDENT_REVIEW" or evidence.get("status")!="CLEARED_AFTER_INDEPENDENT_REVIEW":
        raise ValueError("inconsistent legal clearance status")
    review_artifact(root,{**clear,"decision":clear.get("status")},sha)
    return {"license_artifacts":"VERIFIED_PRESERVED",
            "independent_clearance":"REVIEW_EVIDENCE_PRESENT",
            "redistribution_rights":"INDEPENDENT_HUMAN_DETERMINATION_REFERENCED",
            "upstream_families":3,"historical_sources":len(catalog)}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--check",action="store_true",required=True)
    p.parse_args()
    print(json.dumps(check(),sort_keys=True,ensure_ascii=False))
