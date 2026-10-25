"""Beta isolation, content-addressed asset, source-priority and routing regressions."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import beta_channel

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "LoonKit.lcf"
BETA = ROOT / "beta/LoonKit.lcf"
META = ROOT / "build/beta_manifest.json"
SOURCE = ROOT / "rules/beta/policy_overrides.json"


def section(data: str, label: str) -> str:
    return data.split("[" + label + "]", 1)[1].split("\n[", 1)[0]


def match(host: str, text: str) -> bool:
    if text.startswith('AND,'):
        hit=re.fullmatch(r'AND,\(\((DOMAIN(?:-SUFFIX)?),([^()]+)\),\(NOT,\(\(GEOIP,CN\)\)\)\)',text)
        if not hit:
            return False
        text=hit[1]+','+hit[2]
    parts = text.split(",")
    if len(parts) < 2:
        return False
    kind, value = parts[:2]
    return (
        (kind == "DOMAIN" and host == value) or
        (kind == "DOMAIN-SUFFIX" and (host == value or host.endswith("." + value))) or
        (kind == "DOMAIN-KEYWORD" and value in host)
    )


class BetaChannelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = BASE.read_text(encoding="utf-8")
        cls.beta = BETA.read_text(encoding="utf-8")
        cls.manifest = json.loads(META.read_text())
        cls.policy = json.loads(SOURCE.read_text())
        cls.local = [line for line in section(cls.beta, "Rule").splitlines()
                     if line.startswith(("DOMAIN,", "DOMAIN-SUFFIX,", "DOMAIN-KEYWORD,"))]
        cls.remotes = []
        for entry in section(cls.beta, "Remote Rule").splitlines():
            if not entry.startswith("https://"):
                continue
            uri, *args = entry.split(",")
            props = {k.strip(): v.strip() for a in args if "=" in a
                     for k, v in [a.strip().split("=", 1)]}
            pinned, local_path = uri.split("/loonkit/", 1)[1].split("/", 1)
            allowed = {cls.manifest["immutable_overlay_commit"],
                       cls.manifest["production_release_commit"],
                       cls.manifest["china_direct"]["source_commit"]}
            allowed.update(beta_channel.URI.fullmatch(uri)["sha"]
                           for uri in beta_channel.resource_records(cls.manifest))
            if pinned not in allowed:
                raise AssertionError("unapproved remote pin " + pinned)
            path = ROOT / local_path
            if not path.is_file():
                raise AssertionError("missing immutable local resource: " + local_path)
            cls.remotes.append((props, path))

    def effective(self, host: str, *, without_adblock: bool = False) -> str:
        host = host.lower()
        for line in self.local:
            if match(host, line):
                return line.split(",", 2)[2]
        for props, path in self.remotes:
            if without_adblock and props["policy"] == "AdBlock":
                continue
            # Loon local-first, remote rules in listed order; no plugin block rules.
            for line in path.read_text(encoding="utf-8").splitlines():
                if match(host, line):
                    return props["policy"]
        return "Final"  # Tests only domain inputs; GEOIP/no-resolve requires device/IP path.

    def test_manifest_and_frozen_rule_integrity(self):
        self.assertEqual(hashlib.sha256(self.beta.encode()).hexdigest(),
                         self.manifest["configuration_sha256"])
        self.assertEqual(hashlib.sha256((ROOT / "build/baselines/v6.5.4/LoonKit.lcf").read_bytes()).hexdigest(),
                         self.manifest["original_production_config_sha256"])
        self.assertEqual(self.beta.splitlines()[0], "# LoonKit " + self.manifest["version"] + " · BETA TEST ONLY")
        self.assertEqual(len(self.manifest["overlay_rules"]), 12)
        for item in self.manifest["overlay_rules"].values():
            path = ROOT / beta_channel.URI.fullmatch(item["uri"])["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])
        self.assertEqual(len(self.remotes), self.manifest["runtime_remote_count"])
        self.assertEqual(beta_channel.validate()["resources"], len(self.remotes))

    def test_dns_equal_to_production_and_no_private_dns(self):
        for key in ("dns-server", "doh-server", "hijack-dns", "ip-mode", "ipv6-vif",
                    "interface-mode", "skip-proxy", "bypass-tun", "real-ip"):
            pat = r"(?m)^" + re.escape(key) + r"\s*=.*$"
            self.assertEqual(re.search(pat, section(self.main, "General")).group(),
                             re.search(pat, section(self.beta, "General")).group())
        self.assertIn("https://dns.alidns.com/dns-query", self.beta)
        self.assertNotIn("novaxns", self.beta.lower())
        self.assertIn("GEOIP,CN,DIRECT,no-resolve", section(self.beta, "Rule"))
        self.assertIn("FINAL,Final", section(self.beta, "Rule"))

    def test_adblock_resources_are_reversible(self):
        self.assertFalse(any(x.endswith(",AdBlock") for x in self.local))
        self.assertEqual({p["tag"] for p, _ in self.remotes if p["policy"] == "AdBlock"},
                         {"Beta-AdBlock-Balanced"})
        self.assertEqual(self.effective("analytics.spotify.com"), "AdBlock")
        self.assertEqual(self.effective("analytics.spotify.com", without_adblock=True), "Spotify")
        self.assertEqual(self.effective("pixel.facebook.com", without_adblock=True), "Facebook")
        self.assertEqual(self.effective("copilot.microsoft.com", without_adblock=True), "AI")
        # No broad local ownership can shadow an earlier remote tracking rule.
        for host in ("telemetry.microsoft.com", "events.data.microsoft.com", "pixel.facebook.com"):
            self.assertFalse(any(match(host, x) for x in self.local))

    def test_steam_split_and_unknown_fallback(self):
        for host in ("cm.steampowered.com", "a.steamcontent.com",
                     "a.steamserver.net", "a.steamusercontent.com",
                     "store.steampowered.com"):
            self.assertEqual(self.effective(host), "Steam", host)
        for host in ("dl.steam.ksyna.com", "dl.steam.clngaa.com", "steamchina.com"):
            self.assertEqual(self.effective(host), "DIRECT", host)
        self.assertEqual(self.effective("unregistered-service.example"), "Final")
        self.assertEqual(self.effective("notcolab-specific-example.invalid"), "Final")
        self.assertIn("DOMAIN,copilot.microsoft.com,AI", self.local)

    def test_tls_sni_assisted_ip_target_routing_is_beta_only(self):
        general_beta = section(self.beta, "General")
        general_main = section(self.main, "General")
        self.assertIn("sni-sniffing = true", general_beta)
        self.assertIn("sni-sniffing = true", general_main)
        self.assertRegex(self.manifest["version"], r"v[0-9]+\.[0-9]+\.[0-9]+-beta\.[0-9]+")
        self.assertEqual(self.manifest["candidate_features"]["sni_sniffing"]["status"],
                         "PUBLISHED_BASELINE_FEATURE")
        self.assertIn("GEOIP,CN,DIRECT,no-resolve", section(self.beta, "Rule"))

    def test_china_direct_is_scoped_and_source_is_bit_reproducible(self):
        source = ROOT / "rules/releases/vNext-RC2/ChinaDirect.list"
        scoped = ROOT / beta_channel.URI.fullmatch(self.manifest["china_direct"]["uri"])["path"]
        original = [s for s in source.read_text(encoding="utf-8").splitlines()
                    if s and not s.startswith(("#",";","//"))]
        candidate = [s for s in scoped.read_text(encoding="utf-8").splitlines()
                     if s and not s.startswith(("#",";","//"))]
        exclusions = [s for s in original if s in {"DOMAIN-SUFFIX,cn", "DOMAIN-SUFFIX,wechat.com", "DOMAIN-SUFFIX,wechatapp.com"} or s.startswith("USER-AGENT,")]
        self.assertEqual(len(original), 114837)
        self.assertEqual(len(exclusions), 62)
        reviewed=json.loads((ROOT/'rules/reviewed/v6.5.8/decisions.json').read_text())
        row=next(r for r in reviewed['rules'] if r['tag']=='Beta-ChinaDirect-Scoped')
        self.assertEqual(len(candidate), 114709)
        self.assertEqual(len(row['remove_exact']),66)
        self.assertEqual(candidate, [s for s in original if s not in exclusions and s not in row['remove_exact']])
        self.assertFalse(any(s == "DOMAIN-SUFFIX,cn" or s.startswith("USER-AGENT,")
                             for s in candidate))
        self.assertEqual(hashlib.sha256(scoped.read_bytes()).hexdigest(),
                         self.manifest["china_direct"]["sha256"])
        self.assertEqual(self.effective("unlisted-special-case.cn"), "Final")
        self.assertEqual(self.effective("api.weixin.qq.com"), "DIRECT")
        self.assertEqual(self.effective("wechat.com"), "Final")

    def test_no_lie_about_selector_direct(self):
        self.assertIn("AdBlock = select,REJECT,Proxy", section(self.beta, "Proxy Group"))
        self.assertNotIn("AdBlock = select,REJECT,DIRECT", self.beta)
        self.assertNotIn("policy=PASS", self.beta)

    def test_critical_functions_and_shared_dependencies(self):
        for host, owner in {"crl.microsoft.com":"Microsoft", "ocsp.godaddy.com":"Final",
                            "ocsp.apple.com":"Apple", "api.statsig.com":"Proxy",
                            "tenant.apis.google.com":"Google", "room.host.livekit.cloud":"Proxy"}.items():
            self.assertEqual(self.effective(host), owner, host)
        self.assertEqual(len(self.local), 4)
        self.assertEqual(self.effective("browser-intake-datadoghq.com"), "AdBlock")


if __name__ == "__main__":
    unittest.main()
