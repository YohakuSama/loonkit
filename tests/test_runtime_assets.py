"""Reject incomplete, mutable or damaged runtime dependencies before release."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import runtime_assets as assets


class RuntimeAssetTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.prefix = "https://raw.githubusercontent.com/YohakuSama/loonkit/" + "a" * 40 + "/"
        self.files = {"rules/test.lsr": b"DOMAIN,example.com\n",
                      "icons/test.png": b"test image bytes",
                      "scripts/test.js": b"$done({content:'ok'});\n"}
        self.files["release/test.plugin"] = (
            "#!icon = " + self.prefix + "icons/test.png\n[Argument]\n[Script]\n"
            'generic then script("' + self.prefix + 'scripts/test.js", {}) with tag="Test"\n').encode()
        for name, content in self.files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.profile = ("[Proxy Group]\nProxy = select,DIRECT,img-url = " + self.prefix + "icons/test.png\n"
                        "[Remote Rule]\n" + self.prefix + "rules/test.lsr, policy=Proxy, tag=Test, enabled=true\n"
                        "[Rule]\nFINAL,Proxy\n[Plugin]\n" + self.prefix + "release/test.plugin, enabled=true\n")
        (self.root / "LoonKit.lcf").write_text(self.profile)
        (self.root / "build").mkdir()
        self.write_lock()

    def write_lock(self):
        lock = assets.build_lock(self.root)
        (self.root / assets.LOCK).write_text(json.dumps(lock))
        return lock

    def test_remote_verification_reaches_plugins_scripts_icons_and_rules(self):
        fetched = []

        def fetch(uri, **kwargs):
            fetched.append(uri)
            response = io.BytesIO(self.files[uri.removeprefix(self.prefix)])
            response.geturl = lambda: uri
            return response

        with patch.object(assets, "urlopen", side_effect=fetch):
            self.assertEqual(assets.check(self.root, remote=True)["assets"], 4)
        self.assertEqual(set(fetched), {self.prefix + p for p in self.files})

    def test_mutable_profile_plugin_url_is_rejected(self):
        profile = self.profile.replace(self.prefix + "release/", self.prefix.replace("a" * 40, "main") + "release/")
        (self.root / "LoonKit.lcf").write_text(profile)
        with self.assertRaisesRegex(ValueError, "immutable"):
            assets.check(self.root)

    def test_mutable_transitive_script_cannot_be_hidden_by_new_plugin_digest(self):
        path = self.root / "release/test.plugin"
        path.write_text(path.read_text().replace(self.prefix + "scripts/", self.prefix.replace("a" * 40, "main") + "scripts/"))
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.write_lock()

    def test_modified_script_and_icon_fail_without_rewriting_lock(self):
        locked = (self.root / assets.LOCK).read_bytes()
        for name in ("scripts/test.js", "icons/test.png"):
            path = self.root / name
            before = path.read_bytes()
            path.write_bytes(before + b"changed")
            with self.assertRaisesRegex(ValueError, "differ"):
                assets.check(self.root)
            path.write_bytes(before)
            self.assertEqual((self.root / assets.LOCK).read_bytes(), locked)

    def test_missing_extra_and_duplicate_lock_entries_are_rejected(self):
        lock = self.write_lock()
        for rows in (lock["resources"][:-1], lock["resources"] + [lock["resources"][0]]):
            (self.root / assets.LOCK).write_text(json.dumps({**lock, "resources": rows}))
            with self.assertRaises(ValueError):
                assets.check(self.root)

    def test_extra_unreferenced_resource_is_rejected(self):
        lock = self.write_lock()
        row = dict(lock["resources"][0], uri=self.prefix + "icons/unused.png", path="icons/unused.png")
        (self.root / assets.LOCK).write_text(json.dumps({**lock, "resources": lock["resources"] + [row]}))
        with self.assertRaisesRegex(ValueError, "differ"):
            assets.check(self.root)

    def test_remote_script_damage_and_redirect_are_rejected(self):
        for redirected in (False, True):
            def fetch(uri, **kwargs):
                raw = self.files[uri.removeprefix(self.prefix)]
                response = io.BytesIO(raw + (b"damage" if uri.endswith(".js") else b""))
                response.geturl = lambda: uri + "?redirected" if redirected else uri
                return response
            with patch.object(assets, "urlopen", side_effect=fetch):
                with self.assertRaisesRegex(ValueError, "differs|redirected"):
                    assets.check(self.root, remote=True)

    def test_paths_cannot_escape_repository(self):
        for uri in (self.prefix + "../escape.js", self.prefix.replace("raw.githubusercontent.com", "evil.example") + "script.js"):
            with self.assertRaises(ValueError):
                assets.pinned(uri)
        lock = self.write_lock()
        lock["resources"][0]["local_path"] = "../outside"
        (self.root / assets.LOCK).write_text(json.dumps(lock))
        with self.assertRaisesRegex(ValueError, "escapes"):
            assets.check(self.root)


if __name__ == "__main__":
    unittest.main()
