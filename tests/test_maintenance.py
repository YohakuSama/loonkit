"""Regression guards for read-only releases, rule grammar, upstream parsing and offline triage."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rule_engine
import upstream_review
import verify_release
import verify_upstream_coverage
import route_diagnostics


class PublicChecksumTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "release").mkdir()
        self.profile = b"# LoonKit v6.5.2\n[General]\n"
        (self.root / "LoonKit.lcf").write_bytes(self.profile)
        self.digest = hashlib.sha256(self.profile).hexdigest()
        self.spec = {"stable_release_version": "v6.5.2"}
        self.manifest = {"label": "v6.5.2", "profile_sha256": {"LoonKit.lcf": self.digest}}
        self.sums = self.root / "release/SHA256SUMS.v6.5.2"
        self.doc = self.root / "docs/RELEASE_CHECKSUM_v6.5.2.md"
        self.sums.write_text(self.digest + "  LoonKit.lcf\n", encoding="utf-8")
        self.doc.write_text("# LoonKit v6.5.2\n\n" + self.digest + "  LoonKit.lcf\n", encoding="utf-8")

    def check(self):
        return verify_release.check_public_checksums(self.root, self.manifest, self.spec)

    def test_matching_outputs_pass(self):
        self.assertEqual(self.check(), self.digest)

    def test_corrupt_public_checksum_is_rejected(self):
        self.sums.write_text("0" * 64 + "  LoonKit.lcf\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA256SUMS"):
            self.check()

    def test_alternate_checksum_document_is_rejected(self):
        self.doc.write_text("# v6.5.2\n" + "1" * 64 + "  LoonKit.lcf\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "documentation"):
            self.check()

    def test_unexpected_profile_change_cannot_be_hidden_by_manifest(self):
        (self.root / "LoonKit.lcf").write_bytes(b"unexpected changed release")
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.check()

    def test_duplicate_and_missing_checksum_files_are_rejected(self):
        (self.root / "release/SHA256SUMS.v6.5.1").write_text("old\n")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.check()
        (self.root / "release/SHA256SUMS.v6.5.1").unlink()
        self.doc.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.check()

    def test_new_version_retains_immutable_v652_checksums(self):
        old_digest = "e98dc568485ac4be1240a475e6c2beee60feb9ab5ce3afc19e7d96be81f6a5de"
        self.spec["stable_release_version"] = "v6.5.3"
        self.manifest["label"] = "v6.5.3"
        self.sums.rename(self.root / "release/SHA256SUMS.v6.5.3")
        self.doc.rename(self.root / "docs/RELEASE_CHECKSUM_v6.5.3.md")
        current_doc = self.root / "docs/RELEASE_CHECKSUM_v6.5.3.md"
        current_doc.write_text("# v6.5.3\n" + self.digest + "  LoonKit.lcf\n", encoding="utf-8")
        old_sums = self.root / "release/SHA256SUMS.v6.5.2"
        old_doc = self.root / "docs/RELEASE_CHECKSUM_v6.5.2.md"
        old_sums.write_text(old_digest + "  LoonKit.lcf\n", encoding="utf-8")
        old_doc.write_text("# v6.5.2 historical\n" + old_digest + "  LoonKit.lcf\n", encoding="utf-8")
        self.assertEqual(self.check(), self.digest)
        old_sums.write_text(self.digest + "  LoonKit.lcf\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA256SUMS"):
            self.check()
        old_sums.write_text(old_digest + "  LoonKit.lcf\n", encoding="utf-8")
        old_doc.write_text("# v6.5.2 historical\n" + self.digest + "  LoonKit.lcf\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "documentation"):
            self.check()

    def test_v654_preserves_v653_and_v652_checksums(self):
        v652 = "e98dc568485ac4be1240a475e6c2beee60feb9ab5ce3afc19e7d96be81f6a5de"
        v653 = "3ca24609dadd075a31116c75c0358ec252bf301c15c47bc5c1d98b140832c3a1"
        self.spec["stable_release_version"] = "v6.5.4"
        self.manifest["label"] = "v6.5.4"
        self.sums.rename(self.root / "release/SHA256SUMS.v6.5.4")
        self.doc.rename(self.root / "docs/RELEASE_CHECKSUM_v6.5.4.md")
        (self.root / "docs/RELEASE_CHECKSUM_v6.5.4.md").write_text(
            "# v6.5.4\n" + self.digest + "  LoonKit.lcf\n", encoding="utf-8")
        for version, digest in (("v6.5.2", v652), ("v6.5.3", v653)):
            (self.root / "release" / ("SHA256SUMS." + version)).write_text(
                digest + "  LoonKit.lcf\n", encoding="utf-8")
            (self.root / "docs" / ("RELEASE_CHECKSUM_" + version + ".md")).write_text(
                "# " + version + " historical\n" + digest + "  LoonKit.lcf\n",
                encoding="utf-8")
        self.assertEqual(self.check(), self.digest)
        old = self.root / "release/SHA256SUMS.v6.5.3"
        old.write_text(self.digest + "  LoonKit.lcf\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA256SUMS"):
            self.check()
        old.write_text(v653 + "  LoonKit.lcf\n", encoding="utf-8")
        self.assertEqual(self.check(), self.digest)
        (self.root / "docs/RELEASE_CHECKSUM_v6.5.2.md").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.check()

    def test_wrong_release_title_is_rejected(self):
        self.manifest["label"] = "v6.5.1"
        with self.assertRaisesRegex(ValueError, "version mismatch"):
            self.check()


class RuleEngineTests(unittest.TestCase):
    def test_ip_normalization_and_domain_ownership(self):
        self.assertEqual(rule_engine.normalize("IP-CIDR, 10.2.3.4/8"),
                         "IP-CIDR,10.0.0.0/8,no-resolve")
        self.assertEqual(rule_engine.normalize("DOMAIN-SUFFIX, Example.COM."),
                         "DOMAIN-SUFFIX,example.com")
        self.assertTrue(rule_engine.covers_domain("DOMAIN-SUFFIX,example.com", "a.example.com"))
        self.assertFalse(rule_engine.covers_domain("DOMAIN-SUFFIX,example.com", "evil-example.com"))

    def test_malformed_rules_fail_closed(self):
        for bad in ("DOMAIN", "DOMAIN,bad host", "IP-CIDR,2001:db8::/32",
                    "DOMAIN,example.com,no-resolve", "IP-CIDR,garbage"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                rule_engine.normalize(bad)

    def test_direct_protected_hosts_do_not_get_widened(self):
        value, reason, _ = rule_engine.filter_rule(
            "ChinaDirect", "DOMAIN-SUFFIX,example.com", ("api.example.com",))
        self.assertIsNone(value)
        self.assertEqual(reason, "DIRECT_PROTECTED_DOMAIN")

    def test_adblock_shared_login_domain_is_excluded(self):
        value, reason, _ = rule_engine.filter_rule(
            "AdBlock", "DOMAIN-SUFFIX,auth0.com", ())
        self.assertIsNone(value)
        self.assertEqual(reason, "ADBLOCK_SHARED_CRITICAL_SERVICE")


class UpstreamParsingTests(unittest.TestCase):
    def test_domainset_exact_suffix_duplicate_and_invalid_line(self):
        rules, evidence = upstream_review.parse_source(
            {"format": "domainset", "min_rules": 2},
            b"example.com\n+.example.org\nexample.com\nbad domain\n")
        self.assertEqual(rules, {"DOMAIN,example.com", "DOMAIN-SUFFIX,example.org"})
        self.assertEqual(evidence["source_duplicates"], 1)
        self.assertEqual(evidence["invalid_count"], 1)
        self.assertTrue(evidence["minimum_satisfied"])

    def test_v2fly_regex_is_evidence_not_executable_rule(self):
        source = {"format": "v2fly", "min_rules": 1}
        rules, evidence = upstream_review.parse_source(
            source, b"full:example.com\nregexp:^.*\\.example\\.org$\n")
        self.assertEqual(rules, {"DOMAIN,example.com"})
        self.assertEqual(evidence["excluded_count"], 1)
        self.assertEqual(evidence["excluded_expressions"][0]["reason"],
                         "HOST_REGEX_CANNOT_SAFELY_WIDEN_TO_SUFFIX")

    def test_unknown_format_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown format"):
            upstream_review.parse_source({"format": "guess"}, b"example.com")


class UpstreamHttpProvenanceTests(unittest.TestCase):
    def test_upstream_etag_modified_and_html_fail_closed(self):
        from unittest.mock import patch
        from io import BytesIO

        class FakeResponse:
            def __init__(self, body: bytes, content_type: str):
                self.body = body
                self.headers = {"ETag": 'W/"version-123"',
                                "Last-Modified": "Mon, 19 Oct 2026 10:00:00 GMT",
                                "Content-Type": content_type}
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def geturl(self):
                return "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Loon/AdvertisingLite/AdvertisingLite.list"
            def read(self, n): return self.body[:n]

        source = {
            "url":"https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Loon/AdvertisingLite/AdvertisingLite.list"
        }
        captured = {}
        with patch.object(upstream_review.request, "urlopen", return_value=FakeResponse(
                b"DOMAIN,ad.example.com\n", "text/plain; charset=utf-8")):
            blob = upstream_review.fetch_source(source, metadata=captured)
        self.assertEqual(blob, b"DOMAIN,ad.example.com\n")
        self.assertEqual(captured["http_etag"], 'W/"version-123"')
        self.assertEqual(captured["http_last_modified"], "Mon, 19 Oct 2026 10:00:00 GMT")
        self.assertEqual(captured["transport"], "HTTPS")
        with patch.object(upstream_review.request, "urlopen", return_value=FakeResponse(
                b"<html>blocked</html>", "text/html")):
            with self.assertRaisesRegex(ValueError, "HTML"):
                upstream_review.fetch_source(source)

    def test_absent_http_version_headers_are_not_invented(self):
        from unittest.mock import patch

        class FakeResponse:
            headers = {"Content-Type": "text/plain"}
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def geturl(self):
                return "https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/google"
            def read(self, n): return b"domain:example.com\n"

        source={"url":"https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/google"}
        info={}
        with patch.object(upstream_review.request, "urlopen", return_value=FakeResponse()):
            upstream_review.fetch_source(source, metadata=info)
        self.assertIsNone(info["http_etag"])
        self.assertIsNone(info["http_last_modified"])


class UpstreamCoverageTests(unittest.TestCase):
    def fixture(self):
        return ({"sources": [{"id": "source-one"}, {"id": "source-two"}]},
                {"source_count": 2, "snapshot_count": 2,
                 "incomplete_sources": 0, "incomplete_groups": [],
                 "publication_allowed": False, "excluded_expressions": 0,
                 "sources_with_exclusions": 0,
                 "sources": [
                     {"id": x, "status": "PARSED_FOR_REVIEW",
                      "excluded_count": 0, "excluded_expressions": [],
                      "invalid_count": 0, "minimum_satisfied": True,
                      "sha256": "a" * 64}
                     for x in ("source-one", "source-two")]})

    def test_complete_review_is_not_publication_permission(self):
        catalog, report = self.fixture()
        result = verify_upstream_coverage.assess(report, catalog)
        self.assertTrue(result["coverage_complete"])
        self.assertTrue(result["translation_complete"])
        self.assertIs(report["publication_allowed"], False)

    def test_missing_and_malformed_sources_fail_coverage(self):
        catalog, report = self.fixture()
        report["sources"].pop()
        result = verify_upstream_coverage.assess(report, catalog)
        self.assertFalse(result["coverage_complete"])
        self.assertTrue(any("Missing source IDs" in x for x in result["problems"]))
        _, report = self.fixture()
        report["sources"][0]["minimum_satisfied"] = False
        self.assertFalse(verify_upstream_coverage.assess(report, catalog)["coverage_complete"])


class OfflineDiagnosticsTests(unittest.TestCase):
    def test_har_is_classified_and_sensitive_values_are_not_exposed(self):
        raw = json.dumps({"log": {"entries": [
            {"request": {"url": "https://accounts.spotify.com/login?token=SECRET"},
             "response": {"status": 403}, "_policy": "Private-Node"},
            {"request": {"url": "https://foo.example.net/user?auth=SECRET"},
             "response": {"status": 200}, "_policy": "DIRECT"}]}}).encode()
        report = route_diagnostics.sanitized_log_summary(
            raw, {"Spotify": ("spotify.com",)})
        self.assertEqual(report["processed_requests"], 2)
        self.assertIn({"service": "Spotify", "http_status": "4xx",
                       "policy": "未知", "count": 1}, report["groups"])
        serialized = json.dumps(report, ensure_ascii=False)
        for secret in ("SECRET", "accounts.spotify.com", "Private-Node", "foo.example.net"):
            self.assertNotIn(secret, serialized)

    def test_har_shape_and_size_are_bounded(self):
        with self.assertRaises(ValueError):
            route_diagnostics.sanitized_log_summary(b"[]", {})
        with self.assertRaisesRegex(ValueError, "10 MiB"):
            route_diagnostics.sanitized_log_summary(
                b"x" * (route_diagnostics.MAX_LOG_SIZE + 1), {})

    def test_offline_url_rejects_unsafe_hosts(self):
        self.assertIsNone(route_diagnostics._host("file:///etc/passwd"))
        self.assertIsNone(route_diagnostics._host("https://127.0.0.1/path"))
        self.assertEqual(route_diagnostics.service_for("sub.spotify.com",
                         {"Spotify": ("spotify.com",)}), "Spotify")



class WorkingTreeCleanupTests(unittest.TestCase):
    def test_retired_unreferenced_scripts_do_not_reappear(self):
        root = Path(__file__).resolve().parents[1]
        retired = (
            "scripts/check_sources.py",
            "scripts/prepare_release.py",
            "scripts/v20261025r1/node-intelligence.js",
            "scripts/v20261025r1/media-unlock.js",
            "scripts/v20261025r2/node-intelligence.js",
        )
        for path in retired:
            with self.subTest(path=path):
                self.assertFalse((root / path).exists(), path)

    def test_current_helpers_and_historical_beta_fixtures_survive(self):
        root = Path(__file__).resolve().parents[1]
        for path in (
            "scripts/release_engine.py",
            "scripts/source_lock.py",
            "scripts/review_source.py",
            "scripts/v20261025r3/node-intelligence.js",
            "scripts/v20261025r1/network-diagnostics.js",
            "scripts/v20261025r2/media-unlock.js",
            "scripts/v20261022r11/node-intelligence.js",
            "scripts/v20261022r11/network-diagnostics.js",
            "scripts/v20261022r11/media-unlock.js",
            "build/baselines/generated/v7.0.7/LoonKit.lcf",
            "rules/releases/v7.0.3/AdBlockBalanced.lsr",
            "rules/releases/v7.0.5/ChinaDirect.lsr",
        ):
            with self.subTest(path=path):
                self.assertTrue((root / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
