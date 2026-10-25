"""Verify published strategy icons are consistent and traceable to App Store listings."""
import hashlib
import json
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / "icons"
SIX = {"GitHub", "ChatGPT", "Gemini", "Claude", "Speedtest", "Cloudflare"}

class AppStoreIconTests(unittest.TestCase):
    def test_six_normalized_icons_and_provenance(self):
        manifest = json.loads((ICONS / "appstore_sources.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["icons"]), SIX)
        for group, detail in manifest["icons"].items():
            with self.subTest(group=group):
                data = (ICONS/(group+".png")).read_bytes()
                self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertEqual(data[12:16], b"IHDR")
                self.assertEqual(struct.unpack(">II", data[16:24]), (512,512))
                self.assertEqual(data[25], 6, "RGBA color type required")
                self.assertEqual(hashlib.sha256(data).hexdigest(), detail["sha256"])
                self.assertEqual(detail["output_dimensions"],[512,512])
                self.assertGreater(detail["app_store_id"],0)
                self.assertTrue(detail["app_store_url"].startswith("https://apps.apple.com/"))
                self.assertTrue(detail["artwork_url"].startswith("https://is"))

    def test_only_glass_frame_icons_are_cropped(self):
        manifest = json.loads((ICONS / "appstore_sources.json").read_text(encoding="utf-8"))
        for name in SIX:
            actual = manifest["icons"][name]["glass_edge_trim_pixels"]
            expected = {"GitHub":25, "ChatGPT":25, "Gemini":20}.get(name, 0)
            self.assertEqual(actual, expected)

if __name__ == "__main__":
    unittest.main()
