"""Generated drafts must rebuild exactly, including several cumulative updates.

All source responses, commits and example hosts here are synthetic. Nothing is
sent to GitHub or used as live upstream or device evidence.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import beta_channel
import beta_profile
import beta_upstream_delivery as delivery
from test_beta_upstream_delivery import FakeGitHub


class BetaUpstreamRoundtripTests(unittest.TestCase):
    def test_successive_owner_updates_keep_pins_counts_and_reproducible_profile(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            for folder in ("rules", "build", "beta", "docs", "release", "icons", "scripts"):
                shutil.copytree(ROOT / folder, root / folder)
            shutil.copy2(ROOT / "LoonKit.lcf", root / "LoonKit.lcf")
            shutil.copy2(ROOT / "README.md", root / "README.md")
            stable = (root / "LoonKit.lcf").read_bytes()
            for index, group in enumerate(("YouTube", "Netflix", "YouTube"), 1):
                with self.subTest(update=index, group=group):
                    profile = (root / "beta/LoonKit.lcf").read_bytes()
                    meta = json.loads((root / "build/beta_manifest.json").read_text())
                    catalog = json.loads((root / "rules/sources.json").read_text())
                    api = FakeGitHub(profile, meta, catalog)
                    api.files["docs/BETA_ACCEPTANCE_TEMPLATE.json"] = (root / "docs/BETA_ACCEPTANCE_TEMPLATE.json").read_bytes()
                    for item in meta["upstream_overlays"].values():
                        path = beta_channel.URI.fullmatch(item["uri"])["path"]
                        api.files[path] = (root / path).read_bytes()
                    source_id = next(s["id"] for s in catalog["sources"] if s["group"] == group)
                    rule = "DOMAIN,synthetic-roundtrip-" + str(index) + ".example.test"
                    plan = {
                        "schema_version": 1, "repository": delivery.REPOSITORY,
                        "base_commit": api.base, "version": delivery.next_version(meta["version"]),
                        "base_configuration_sha256": delivery.digest(profile),
                        "runtime_baseline": True, "source_integrity_complete": True,
                        "source_count": len(catalog["sources"]),
                        "sources": [{"id": s["id"], "group": s["group"], "url": s.get("url"),
                                     "sha256": "c" * 64, "status": "PARSED_FOR_REVIEW"}
                                    for s in catalog["sources"]],
                        "groups": {group: {"rules": [rule], "provenance": {rule: [source_id]}}},
                        "full_diff_sha256": "d" * 64,
                        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    }
                    result = delivery.publish(plan, api)
                    for path, payload in api.writes:
                        if path == "/git/trees":
                            for entry in payload["tree"]:
                                target = root / entry["path"]
                                target.parent.mkdir(parents=True, exist_ok=True)
                                target.write_text(entry["content"])
                    updated = json.loads((root / "build/beta_manifest.json").read_text())
                    beta_channel.validate(root)
                    from release_engine import check as verify_formal
                    self.assertEqual(verify_formal(root=root)["version"], json.loads((root / "build/release_spec.json").read_text())["stable_release_version"])
                    rendered, rebuilt = beta_profile.render(meta["immutable_overlay_commit"], root)
                    self.assertEqual(rendered, (root / "beta/LoonKit.lcf").read_bytes())
                    self.assertEqual(rebuilt, updated)
                    self.assertEqual(updated["source_group_counts"][group], meta["source_group_counts"][group] + 1)
                    for owner, prior in meta["upstream_overlays"].items():
                        if owner != group:
                            self.assertEqual(updated["upstream_overlays"][owner], prior)
                    self.assertEqual(updated["candidate_source_commit"], result["asset_commit"])
                    self.assertEqual((root / "LoonKit.lcf").read_bytes(), stable)
                    general = beta_channel.section(rendered.decode(), "General")
                    self.assertEqual(general, beta_channel.section(profile.decode(), "General"))
                    # Template resets must not turn synthetic publication into approval.
                    evidence = json.loads((root / "docs/BETA_ACCEPTANCE_TEMPLATE.json").read_text())
                    self.assertFalse(evidence["maintainer_approved"])
                    self.assertIsNone(evidence["commit_sha"])


if __name__ == "__main__":
    unittest.main()
