#!/usr/bin/env python3
"""Protect navigation boundaries and local links in reader-facing guides."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = (
    "docs/SETUP_GUIDE.md",
    "docs/LOON_APP_SETTINGS.md",
    "docs/NODE_SELECTION.md",
    "docs/DNS_PRIVACY.md",
    "docs/NETWORK_DIAGNOSTICS.md",
    "rules/README.md",
)
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


class DocumentationNavigationTests(unittest.TestCase):
    def test_local_links_in_navigation_and_guides_are_valid(self):
        for name in ("README.md",) + PAGES:
            page = ROOT / name
            text = page.read_text(encoding="utf-8")
            for raw in LINK.findall(text):
                target = raw.split("#", 1)[0].split("?", 1)[0]
                if not target.startswith(("./", "../")):
                    continue
                resolved = (page.parent / target).resolve()
                with self.subTest(source=name, link=raw):
                    self.assertTrue(resolved.is_relative_to(ROOT), "link escapes repository")
                    self.assertTrue(resolved.exists(), "broken local link")

    def test_each_guide_has_its_own_purpose(self):
        docs = {name: (ROOT / name).read_text(encoding="utf-8") for name in PAGES}
        expected = {
            "docs/SETUP_GUIDE.md": "初次导入",
            "docs/LOON_APP_SETTINGS.md": "配置托管",
            "docs/NODE_SELECTION.md": "节点选择",
            "docs/DNS_PRIVACY.md": "DNS",
            "docs/NETWORK_DIAGNOSTICS.md": "网络辅助",
            "rules/README.md": "分流规则",
        }
        seen_titles = set()
        for name, key in expected.items():
            h1 = [line for line in docs[name].splitlines() if line.startswith("# ")]
            with self.subTest(document=name):
                self.assertEqual(len(h1), 1)
                self.assertIn(key, h1[0])
                self.assertNotIn(h1[0], seen_titles)
                seen_titles.add(h1[0])
        self.assertNotIn("DoH 流量模式", docs["docs/SETUP_GUIDE.md"])
        self.assertNotIn("223.5.5.5", docs["docs/LOON_APP_SETTINGS.md"])
        self.assertNotIn("现役配置：**v7.0.9**", docs["rules/README.md"])

    def test_no_copy_pasted_long_instructions_across_guides(self):
        seen = {}
        for name in PAGES:
            for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
                line = re.sub(r"^[>|*+\-]\s*", "", line.strip())
                # Short command names, menu labels and tables are useful shared vocabulary.
                if len(line) < 90 or line.startswith(("|", "http", "`", "#")):
                    continue
                with self.subTest(document=name, excerpt=line[:40]):
                    self.assertNotIn(line, seen, "same long guidance also in " + seen.get(line, ""))
                seen[line] = name


if __name__ == "__main__":
    unittest.main()
