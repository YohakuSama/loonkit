"""Version-independent release renderer regression tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import release_engine


class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "build" / "baselines").mkdir(parents=True)
        (self.root / "docs").mkdir()
        (self.root / "release").mkdir()
        self.raw = b"# LoonKit v1.0.0\n[Rule]\nDOMAIN,example.org,DIRECT\nFINAL,Final\n"
        (self.root / "build" / "baselines" / "base.lcf").write_bytes(self.raw)
        self.recipe = {"schema_version": 1, "target_version": "v1.0.1",
                       "base": {"path": "build/baselines/base.lcf",
                                "sha256": hashlib.sha256(self.raw).hexdigest()},
                       "changes": [{"find": "DOMAIN,example.org,DIRECT",
                                    "replace": "DOMAIN,example.org,Proxy"}]}

    def test_exact_render_and_version_header(self):
        profile = release_engine.render(self.root, self.recipe)
        self.assertEqual(profile, self.raw.replace(b"v1.0.0", b"v1.0.1")
                         .replace(b"example.org,DIRECT", b"example.org,Proxy"))

    def test_ambiguous_change_is_rejected(self):
        recipe = dict(self.recipe, changes=[{"find": "DIRECT", "replace": "Proxy"}])
        # The base has a single DIRECT, so add a second one to create ambiguity.
        modified = self.raw.replace(b"FINAL,Final", b"DOMAIN,foo.org,DIRECT\nFINAL,Final")
        (self.root / "build" / "baselines" / "base.lcf").write_bytes(modified)
        recipe["base"] = dict(recipe["base"], sha256=hashlib.sha256(modified).hexdigest())
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            release_engine.render(self.root, recipe)

    def test_modified_baseline_is_rejected(self):
        (self.root / "build" / "baselines" / "base.lcf").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "baseline"):
            release_engine.render(self.root, self.recipe)

    def test_traversal_and_noop_are_rejected(self):
        malicious = dict(self.recipe, base={"path": "../outside.lcf",
                                           "sha256": self.recipe["base"]["sha256"]})
        with self.assertRaisesRegex(ValueError, "escapes"):
            release_engine.render(self.root, malicious)
        noop = dict(self.recipe, changes=[{"find": "a", "replace": "a"}])
        with self.assertRaisesRegex(ValueError, "no-op"):
            release_engine.render(self.root, noop)

    def test_next_version_requires_no_new_python_script(self):
        old_hash = hashlib.sha256(self.raw).hexdigest()
        (self.root / "LoonKit.lcf").write_bytes(self.raw)
        (self.root / "README.md").write_text("当前版本：**v1.0.0**\n")
        spec = {"stable_release_version": "v1.0.0", "release_engine": "generic",
                "historical_profile_sha256": {}}
        meta = {"label": "v1.0.0", "profile_sha256": {"LoonKit.lcf": old_hash}}
        (self.root / "build" / "release_spec.json").write_text(json.dumps(spec))
        (self.root / "build" / "release_manifest.json").write_text(json.dumps(meta))
        with patch.object(release_engine, "check", return_value={}):
            digest = release_engine.start_next(self.root, "v1.0.1", require_clean=False)
        self.assertEqual(digest, hashlib.sha256((self.root / "LoonKit.lcf").read_bytes()).hexdigest())
        self.assertEqual(release_engine.render(self.root), (self.root / "LoonKit.lcf").read_bytes())
        self.assertIn("v1.0.1", (self.root / "README.md").read_text())
        self.assertEqual(json.loads((self.root / "build" / "release_spec.json").read_text())
                         ["historical_profile_sha256"]["v1.0.0"], old_hash)
        self.assertEqual((self.root / "release" / "SHA256SUMS.v1.0.1").read_text().split()[0], digest)


    def test_dirty_checkout_fails_before_any_write(self):
        with patch.object(release_engine, "require_clean_git_checkout",
                          side_effect=ValueError("working tree is dirty")):
            with self.assertRaisesRegex(ValueError, "dirty"):
                release_engine.start_next(self.root, "v1.0.1")
        self.assertFalse((self.root / "LoonKit.lcf").exists())

    def test_partial_output_replacement_rolls_back_every_file(self):
        from unittest.mock import patch
        original = release_engine.os.replace
        before = b"unchanged old checksum"
        original_file = self.root / "release" / "existing.txt"
        original_file.write_bytes(before)
        outputs = {"release/existing.txt": b"new",
                   "docs/new.txt": b"new"}
        calls = [0]

        def inject_failure(src, dst):
            calls[0] += 1
            if calls[0] == 2:
                raise OSError("simulated filesystem failure")
            return original(src, dst)

        with patch.object(release_engine.os, "replace", side_effect=inject_failure):
            with self.assertRaisesRegex(OSError, "simulated"):
                release_engine.apply_outputs(self.root, outputs)
        self.assertEqual(original_file.read_bytes(), before)
        self.assertFalse((self.root / "docs" / "new.txt").exists())

    def test_distinct_versioned_snapshot_is_not_overwritten(self):
        version = "v1.0.0"
        path = self.root / "build" / "baselines" / "generated" / version / "LoonKit.lcf"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"wrong snapshot")
        (self.root / "LoonKit.lcf").write_bytes(self.raw)
        (self.root / "build" / "release_spec.json").write_text(json.dumps({"stable_release_version":"v1.0.0", "release_engine":"generic"}))
        with patch.object(release_engine, "check", return_value={}):
            with self.assertRaisesRegex(ValueError, "historical snapshot differs"):
                release_engine.start_next(self.root, "v1.0.1", require_clean=False)
        self.assertEqual(path.read_bytes(), b"wrong snapshot")

if __name__ == "__main__":
    unittest.main()
