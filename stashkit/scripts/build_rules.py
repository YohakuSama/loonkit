#!/usr/bin/env python3
"""Regenerate Stash-native text assets from the LoonKit release manifest.

This script only updates rule files. Review and update StashKit.yaml and version
metadata separately when production categories or policy groups change.
"""
import json
from pathlib import Path
from verify import ROOT, KIT, generate_source_sets

manifest = json.loads((ROOT / "build/release_manifest.json").read_text(encoding="utf-8"))
outdir = KIT / "rules"
outdir.mkdir(parents=True, exist_ok=True)
expected = set()
for item in manifest["runtime_resources"]:
    source = ROOT / item["path"]
    groups, count = generate_source_sets(source)
    if count != item["matcher_count"]:
        raise ValueError(f"Source mismatch: {source}")
    base = source.stem
    for kind, content in groups.items():
        if not content:
            continue
        output = outdir / (base + "." + kind + ".txt")
        expected.add(output)
        output.write_text(
            "# StashKit " + base + " " + kind + " from LoonKit " + manifest["label"] + "\n"
            + "\n".join(content) + "\n",
            encoding="utf-8",
        )
for obsolete in outdir.glob("*.txt"):
    if obsolete not in expected:
        raise RuntimeError(f"Obsolete asset requires manual review: {obsolete}")
print(f"Generated {len(expected)} Stash-native rule sets from "
      f"{len(manifest['runtime_resources'])} LoonKit sources.")
