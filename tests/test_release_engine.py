"""Structured release generation, semantic validation and safe version upgrades."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import profile_model
import release_engine
import runtime_assets


class StructuredReleaseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.prefix = "https://raw.githubusercontent.com/YohakuSama/loonkit/" + "a" * 40 + "/"
        self.model = {
            "schema_version": 1, "general": {"dns-server": "223.5.5.5"},
            "filters": [{"name": "All", "pattern": ".*"}],
            "groups": [
                {"name": "Proxy", "type": "select", "members": ["All"], "options": {}, "icon": self.prefix + "icons/test.png"},
                {"name": "Final", "type": "select", "members": ["Proxy", "DIRECT"], "options": {}, "icon": self.prefix + "icons/test.png"}],
            "remote_rules": [{"uri": self.prefix + "rules/releases/test.lsr", "policy": "Proxy", "tag": "Example", "source_group": "Example"}],
            "hosts": {},
            "rules": [{"type": "GEOIP", "value": "CN", "policy": "DIRECT", "flags": ["no-resolve"]},
                      {"type": "FINAL", "value": "", "policy": "Final", "flags": []}],
            "plugins": [self.prefix + "release/test.plugin"], "service_roots": {}}
        self.spec = {"schema_version": 3, "release_engine": "structured", "status": "FORMAL_RELEASE",
                     "stable_release_version": "v1.0.0", "historical_profile_sha256": {}}
        files = {
            "build/profile.json": json.dumps(self.model).encode(),
            "build/release_spec.json": json.dumps(self.spec).encode(),
            "README.md": "当前版本：**v1.0.0**\n".encode(),
            "rules/releases/test.lsr": b"DOMAIN,example.org\n",
            "icons/test.png": b"test icon",
            "scripts/test.js": b"$done('ok');\n",
            "release/test.plugin": ('[Argument]\n[Script]\ngeneric then script("' + self.prefix + 'scripts/test.js", {}) with tag="Test"\n').encode(),
        }
        for name, raw in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        # Frozen-input lineage is verified separately by the source-lock suite.
        self.gate = patch.object(release_engine, "check_lock", return_value={}).start()
        self.addCleanup(patch.stopall)
        release_engine.write(self.root)
        self.relock()

    def relock(self):
        (self.root / runtime_assets.LOCK).write_text(json.dumps(runtime_assets.build_lock(self.root)))

    def save_model(self, model):
        (self.root / profile_model.MODEL).write_text(json.dumps(model))

    def test_render_is_deterministic_and_inventory_is_generated(self):
        profile = (self.root / "LoonKit.lcf").read_bytes()
        self.assertEqual(profile, release_engine.render(self.root))
        self.assertEqual(profile, profile_model.render(copy.deepcopy(self.model), "v1.0.0"))
        manifest = json.loads((self.root / "build/release_manifest.json").read_text())
        self.assertEqual(manifest["remote_rule_count"], 1)
        self.assertEqual(release_engine.check(self.root)["resources"], 1)
        path = self.root / "rules/releases/added.lsr"
        path.write_text("DOMAIN,added.example\nDOMAIN,other.example\n")
        changed = copy.deepcopy(self.model)
        changed["remote_rules"].append({"uri": self.prefix + "rules/releases/added.lsr", "policy": "Proxy", "tag": "Added", "source_group": "Example"})
        self.save_model(changed)
        release_engine.write(self.root)
        self.relock()
        manifest = json.loads((self.root / "build/release_manifest.json").read_text())
        self.assertEqual([r["tag"] for r in manifest["runtime_resources"]], ["Example", "Added"])
        self.assertEqual(manifest["remote_rule_count"], 3)
        self.assertEqual(manifest["source_group_counts"], {"Example": 3})
        self.assertEqual(release_engine.check(self.root)["resources"], 2)

    def test_undefined_references_are_rejected_before_writing(self):
        before = (self.root / "LoonKit.lcf").read_bytes()
        for area in ("group", "remote", "local"):
            changed = copy.deepcopy(self.model)
            if area == "group": changed["groups"][0]["members"] = ["MissingPolicy"]
            elif area == "remote": changed["remote_rules"][0]["policy"] = "MissingPolicy"
            else: changed["rules"][-1]["policy"] = "MissingPolicy"
            self.save_model(changed)
            with self.assertRaisesRegex(ValueError, "undefined"):
                release_engine.write(self.root)
            self.assertEqual((self.root / "LoonKit.lcf").read_bytes(), before)

    def test_policy_cycles_and_duplicate_names_are_rejected(self):
        changed = copy.deepcopy(self.model)
        changed["groups"][0]["members"] = ["Final"]
        with self.assertRaisesRegex(ValueError, "cyclic"):
            profile_model.render(changed, "v1.0.0")
        changed = copy.deepcopy(self.model)
        changed["groups"].append(copy.deepcopy(changed["groups"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            profile_model.render(changed, "v1.0.0")

    def test_mutable_assets_and_unknown_fields_are_rejected(self):
        for area in ("plugin", "icon", "remote", "schema"):
            changed = copy.deepcopy(self.model)
            if area == "plugin": changed["plugins"][0] = changed["plugins"][0].replace("a" * 40, "main")
            elif area == "icon": changed["groups"][0]["icon"] = changed["groups"][0]["icon"].replace("a" * 40, "main")
            elif area == "remote": changed["remote_rules"][0]["uri"] = changed["remote_rules"][0]["uri"].replace("a" * 40, "main")
            else: changed["unreviewed_raw_section"] = "[Script]\n"
            with self.assertRaises(ValueError):
                profile_model.render(changed, "v1.0.0")

    def test_fallback_and_broad_rule_order_cannot_silently_change(self):
        changed = copy.deepcopy(self.model)
        changed["rules"].reverse()
        with self.assertRaisesRegex(ValueError, "FINAL"):
            profile_model.render(changed, "v1.0.0")
        changed = copy.deepcopy(self.model)
        changed["rules"][0]["flags"] = []
        with self.assertRaisesRegex(ValueError, "fallback"):
            profile_model.render(changed, "v1.0.0")
        changed = copy.deepcopy(self.model)
        changed["remote_rules"][0]["source_group"] = "ChinaDirect"
        changed["remote_rules"].append({"uri": self.prefix + "rules/releases/later.lsr", "policy": "Proxy", "tag": "Later", "source_group": "Service"})
        with self.assertRaisesRegex(ValueError, "domestic"):
            profile_model.render(changed, "v1.0.0")

    def test_model_profile_and_manifest_drift_are_rejected(self):
        profile = self.root / "LoonKit.lcf"
        original = profile.read_bytes()
        profile.write_bytes(original + b"# drift\n")
        with self.assertRaisesRegex(ValueError, "source model"):
            release_engine.check(self.root)
        profile.write_bytes(original)
        manifest = self.root / "build/release_manifest.json"
        changed = json.loads(manifest.read_text())
        changed["runtime_resources"][0]["policy"] = "DIRECT"
        manifest.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "inventory"):
            release_engine.check(self.root)

    def test_two_successive_versions_need_no_new_code_or_baseline(self):
        original = (self.root / "LoonKit.lcf").read_bytes()
        for version in ("v1.0.1", "v1.0.2"):
            release_engine.start_next(self.root, version, require_clean=False)
            self.assertEqual(release_engine.check(self.root)["version"], version)
        spec = json.loads((self.root / "build/release_spec.json").read_text())
        self.assertEqual(spec["historical_profile_sha256"]["v1.0.0"], hashlib.sha256(original).hexdigest())
        self.assertEqual(self.model, json.loads((self.root / profile_model.MODEL).read_text()))
        self.assertFalse((self.root / "build/baselines").exists())
        self.assertFalse((self.root / "build/release_recipe.json").exists())
        self.assertIn("v1.0.2", (self.root / "README.md").read_text())

    def test_bad_readme_and_dirty_checkout_fail_before_output(self):
        before = (self.root / "LoonKit.lcf").read_bytes()
        with patch.object(release_engine, "require_clean_git_checkout", side_effect=ValueError("working tree is dirty")):
            with self.assertRaisesRegex(ValueError, "dirty"):
                release_engine.start_next(self.root, "v1.0.1")
        (self.root / "README.md").write_text("missing current version")
        with self.assertRaisesRegex(ValueError, "README"):
            release_engine.start_next(self.root, "v1.0.1", require_clean=False)
        self.assertEqual((self.root / "LoonKit.lcf").read_bytes(), before)
        self.assertFalse((self.root / "release/SHA256SUMS.v1.0.1").exists())

    def test_partial_output_replacement_rolls_back_every_file(self):
        original = release_engine.os.replace
        target = self.root / "release/existing.txt"
        target.write_bytes(b"original")
        count = [0]
        def fail(source, destination):
            count[0] += 1
            if count[0] == 2: raise OSError("simulated failure")
            return original(source, destination)
        with patch.object(release_engine.os, "replace", side_effect=fail):
            with self.assertRaisesRegex(OSError, "simulated"):
                release_engine.apply_outputs(self.root, {"release/existing.txt": b"new", "docs/new.txt": b"new"})
        self.assertEqual(target.read_bytes(), b"original")
        self.assertFalse((self.root / "docs/new.txt").exists())


if __name__ == "__main__":
    unittest.main()
