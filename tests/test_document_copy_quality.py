#!/usr/bin/env python3
"""Check reader-facing docs for release-state drift and temporary editing copy."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# These are living user/maintainer references, not dated release notes or audit snapshots.
EVERGREEN = (
    "README.md",
    "docs/SETUP_GUIDE.md",
    "docs/LOON_APP_SETTINGS.md",
    "docs/NODE_SELECTION.md",
    "docs/DNS_PRIVACY.md",
    "docs/NETWORK_DIAGNOSTICS.md",
    "docs/MAINTAINING.md",
    "docs/DEPENDENCIES.md",
    "docs/RULE_SAFETY.md",
    "docs/ROUTE_DIAGNOSTICS.md",
    "docs/BETA_CHANNEL.md",
    "rules/README.md",
    "icons/README.md",
)
TEMPORARY_PHRASES = (
    "本次不修改",
    "本次不改动",
    "本次保持",
    "此次不修改",
    "（保持不变）",
    "新候选 v",
    "已核对的界面",
)


class DocumentationCopyQualityTests(unittest.TestCase):
    def test_evergreen_guides_have_no_editing_session_annotations(self):
        for name in EVERGREEN:
            body = (ROOT / name).read_text(encoding="utf-8")
            for marker in TEMPORARY_PHRASES:
                with self.subTest(document=name, phrase=marker):
                    self.assertNotIn(marker, body)

    def test_dns_and_node_sections_describe_configuration_not_edits(self):
        dns = (ROOT / "docs/DNS_PRIVACY.md").read_text(encoding="utf-8")
        node = (ROOT / "docs/NODE_SELECTION.md").read_text(encoding="utf-8")
        self.assertIn("## LoonKit 默认 DNS 配置", dns)
        self.assertIn("## 默认测速参数", node)
        self.assertIn("DNS 服务器 → 查询回落 → 关闭", (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_current_resource_counts_match_manifest(self):
        manifest = json.loads((ROOT / "build/release_manifest.json").read_text(encoding="utf-8"))
        runtime_lock = json.loads((ROOT / "build/runtime.lock.json").read_text(encoding="utf-8"))
        deps = (ROOT / "docs/DEPENDENCIES.md").read_text(encoding="utf-8")
        rules = (ROOT / "rules/README.md").read_text(encoding="utf-8")
        self.assertIn(f"{manifest['remote_subscription_count']} 份", deps)
        self.assertIn(f"{manifest['remote_subscription_count']} 份", rules)
        self.assertIn(f"{len(runtime_lock['resources'])} 个", deps)

    def test_old_policy_and_rule_counts_are_labelled_historical(self):
        third_party = (ROOT / "docs/THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        design = (ROOT / "docs/BETA_DECISION_REGISTER.md").read_text(encoding="utf-8")
        beta = (ROOT / "docs/BETA_CHANNEL.md").read_text(encoding="utf-8")
        self.assertRegex(third_party, r"历史规则构建曾生成[^\n]*26 份远程规则")
        self.assertIn("不是现行配置统计", third_party)
        self.assertIn("不是当前正式规则的配置说明", design)
        self.assertIn("构建基线为历史正式版本", beta)
        gate = (ROOT / "docs/BETA_PROMOTION_GATE.md").read_text(encoding="utf-8")
        self.assertNotIn("release_gate_file", gate)


if __name__ == "__main__":
    unittest.main()
