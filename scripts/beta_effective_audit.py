#!/usr/bin/env python3
"""Offline, source-aware Loon beta route trace. No network access or user traffic.

This simulates ONLY DOMAIN/DOMAIN-SUFFIX/DOMAIN-KEYWORD names against the
exact immutable resource files referenced by the reviewed beta configuration.
It does not model DNS, SNI/ECH, IP matches, policy-group UI selections, plugin
rewrites, a user's additional plugins, or actual device behavior.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import beta_channel
from regional_rules import condition, permits, source_matcher

ROOT = Path(__file__).resolve().parents[1]
URI = re.compile(
    r"https://raw\.githubusercontent\.com/YohakuSama/loonkit/"
    r"(?P<sha>[a-f0-9]{40})/(?P<path>[^,\s]+)\Z"
)
DOMAIN_KINDS = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"}

# A small, intentionally independent scenario oracle; this list cannot
# silently be regenerated from the engine's actual output.
EXPECTED = {
    "analytics.spotify.com": ("AdBlock", "Spotify"),
    "pixel.facebook.com": ("AdBlock", "Facebook"),
    "telemetry.microsoft.com": ("AdBlock", "Microsoft"),
    "events.data.microsoft.com": ("AdBlock", "Microsoft"),
    "copilot.microsoft.com": ("AI", "AI"),
    "login.microsoftonline.com": ("Microsoft", "Microsoft"),
    "ocsp.apple.com": ("Apple", "Apple"),
    "mesu.apple.com": ("Apple", "Apple"),
    "crl.microsoft.com": ("Microsoft", "Microsoft"),
    "ocsp.godaddy.com": ("Final", "Final"),
    "wechat.com": ("Final", "Final"),
    "wechatapp.com": ("Final", "Final"),
    "tenant-unknown.apis.google.com": ("Google", "Google"),
    "api.statsig.com": ("Proxy", "Proxy"),
    "room.host.livekit.cloud": ("Proxy", "Proxy"),
    "client-api.arkoselabs.com": ("Proxy", "Proxy"),
    "browser-intake-datadoghq.com": ("AdBlock", "Final"),
    "cdn.usefathom.com": ("AdBlock", "Final"),
    "events.statsigapi.net": ("AdBlock", "Final"),
    "abema.tv": ("Abema", "Abema"),
    "abchina.com.cn": ("DIRECT", "DIRECT"),
    "ebank.ccb.com": ("DIRECT", "DIRECT"),
    "notcolab-specific-example.invalid": ("Final", "Final"),
    "www.youtube.com": ("YouTube", "YouTube"),
    "www.netflix.com": ("Netflix", "Netflix"),
    "www.disneyplus.com": ("Disney", "Disney"),
    "www.primevideo.com": ("PrimeVideo", "PrimeVideo"),
    "www.tiktok.com": ("TikTok", "TikTok"),
    "www.bilibili.com": ("Bilibili", "Bilibili"),
    "www.gamer.com.tw": ("動畫瘋", "動畫瘋"),
    "www.dazn.com": ("Dazn", "Dazn"),
    "www.max.com": ("HBO", "HBO"),
    "api.telegram.org": ("Telegram", "Telegram"),
    "www.whatsapp.com": ("Whatsapp", "Whatsapp"),
    "www.instagram.com": ("Instagram", "Instagram"),
    "www.facebook.com": ("Facebook", "Facebook"),
    "www.x.com": ("Twitter", "Twitter"),
    "www.discord.com": ("Discord", "Discord"),
    "www.paypal.com": ("Paypal", "Paypal"),
    "www.bbc.com": ("BBC", "BBC"),
    "www.line.me": ("Line", "Line"),
    "www.reddit.com": ("Reddit", "Reddit"),
    "www.linkedin.com": ("Linkedin", "Linkedin"),
    "www.twitch.tv": ("Twitch", "Twitch"),
    "www.spotify.com": ("Spotify", "Spotify"),
    "www.google.com": ("Google", "Google"),
    "www.amap.com": ("DIRECT", "DIRECT"),
    "www.alipayobjects.com": ("DIRECT", "DIRECT"),
    "www.t3go.cn": ("DIRECT", "DIRECT"),
    "grok.x.com": ("AI", "AI"),
    "notebooklm.google.com": ("AI", "AI"),
    "cm.steampowered.com": ("Steam", "Steam"),
    "downloads.steamcontent.com": ("Steam", "Steam"),
    "downloads.steamusercontent.com": ("Steam", "Steam"),
    "dl.steam.ksyna.com": ("DIRECT", "DIRECT"),
    "api.weixin.qq.com": ("DIRECT", "DIRECT"),
    "unknown-unlisted-tld-proof.cn": ("Final", "Final"),
    "unknown-unlisted-overseas.example": ("Final", "Final"),
}
PENDING = {}
REGIONAL = {'www.apple.com':'Apple','configuration.apple.com':'Apple',
            'download.microsoft.com':'Microsoft','www.paypal.com':'Paypal',
            'www.bilibili.com':'Bilibili','servicewechat.com':'Final'}


def section(data: str, label: str) -> str:
    match = re.search(r"(?m)^\[" + re.escape(label) + r"\]$", data)
    if not match:
        raise ValueError("missing config section " + label)
    rest = data[match.end():]
    tail = re.search(r"(?m)^\[[^\]]+\]$", rest)
    return rest[:tail.start()] if tail else rest


def domain_rule(line: str) -> tuple[str, str] | None:
    columns = [x.strip() for x in source_matcher(line).split(",")]
    if len(columns) < 2 or columns[0] not in DOMAIN_KINDS:
        return None
    return columns[0], columns[1].lower()


def naive_domain_match(host: str, matcher: str) -> bool:
    """Plain baseline oracle for cross-checking the indexed implementation."""
    pair = domain_rule(matcher) if permits(matcher,None) else None
    if pair is None:
        return False
    kind, value = pair
    host = host.lower().rstrip(".")
    if kind == "DOMAIN":
        return value == host
    if kind == "DOMAIN-SUFFIX":
        return value == host or host.endswith("." + value)
    return value in host


class DomainIndex:
    def __init__(self, lines):
        self.exact = {}
        self.suffix = {}
        self.keywords = []
        for row in lines:
            parsed = domain_rule(row)
            if parsed is None:
                continue
            kind, value = parsed
            if kind == "DOMAIN":
                self.exact.setdefault(value, row)
            elif kind == "DOMAIN-SUFFIX":
                self.suffix.setdefault(value, row)
            else:
                self.keywords.append((value, row))

    def match(self, host: str, country: str | None = None):
        host = host.lower().rstrip(".")
        if host in self.exact and permits(self.exact[host], country):
            return self.exact[host]
        labels = host.split(".")
        for at in range(len(labels)):
            name = ".".join(labels[at:])
            if name in self.suffix and permits(self.suffix[name], country):
                return self.suffix[name]
        for keyword, rule in self.keywords:
            if keyword in host and permits(rule, country):
                return rule
        return None


def build(root: Path = ROOT):
    beta_channel.validate(root)
    profile = (root / "beta/LoonKit.lcf").read_text(encoding="utf-8")
    meta = json.loads((root / "build/beta_manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256(profile.encode()).hexdigest() != meta["configuration_sha256"]:
        raise ValueError("beta config checksum mismatch")
    allow = {
        meta["immutable_overlay_commit"],
        meta["production_release_commit"],
        meta["china_direct"]["source_commit"],
    }
    allow.update(URI.fullmatch(uri)["sha"] for uri in beta_channel.resource_records(meta))
    local = []
    for row in section(profile, "Rule").splitlines():
        if not row.strip() or row.lstrip().startswith(("#", ";", "//")):
            continue
        if domain_rule(row):
            cols = row.split(",")
            if len(cols) != 3:
                raise ValueError("local domain rule requires owner policy: " + row)
            local.append((row, cols[2].strip()))
    plugin_entries = [x.strip() for x in section(profile, "Plugin").splitlines()
                      if x.strip() and not x.lstrip().startswith(("#", ";", "//"))]
    if len(plugin_entries) != 1:
        raise ValueError("unreviewed additional plugin in public beta")
    plugin_ref = plugin_entries[0].split(",")[0]
    plugin_match = URI.fullmatch(plugin_ref)
    if not plugin_match:
        raise ValueError("plugin URL not pinned to a commit")
    plugin = (root / plugin_match["path"]).read_text(encoding="utf-8")
    if re.search(r"(?m)^\[(?:Rule|Host|Rewrite)\]$", plugin):
        raise ValueError("active plugin routing/rewrites need an explicit precedence parser")
    remotes = []
    for row in section(profile, "Remote Rule").splitlines():
        if not row.startswith("https://"):
            continue
        pieces = [x.strip() for x in row.split(",")]
        uri_match = URI.fullmatch(pieces[0])
        if not uri_match or uri_match["sha"] not in allow:
            raise ValueError("unreviewed mutable or foreign remote list " + pieces[0])
        flags = dict(x.split("=", 1) for x in pieces[1:] if "=" in x)
        flags = {k.strip(): v.strip() for k, v in flags.items()}
        if flags.get("enabled") != "true" or not flags.get("policy") or not flags.get("tag"):
            raise ValueError("disabled or ownerless remote entry in beta candidate")
        path = root / uri_match["path"]
        raw = path.read_bytes()
        if not raw:
            raise ValueError("empty remote asset " + str(path))
        # Exact hashes are checked elsewhere for formal rules. The beta
        # manifest hashes all ten beta overlays and the new ChinaDirect asset.
        if pieces[0] == meta["china_direct"]["uri"]:
            if hashlib.sha256(raw).hexdigest() != meta["china_direct"]["sha256"]:
                raise ValueError("scoped domestic content hash mismatch")
        else:
            name = path.name.removesuffix(".list")
            if name in meta["overlay_rules"] and (
                hashlib.sha256(raw).hexdigest() != meta["overlay_rules"][name]["sha256"]
            ):
                raise ValueError("beta overlay checksum mismatch: " + name)
        lines = [x.strip() for x in raw.decode("utf-8").splitlines()
                 if x.strip() and not x.lstrip().startswith(("#", ";", "//"))]
        remotes.append({
            "tag": flags["tag"],
            "policy": flags["policy"],
            "file": uri_match["path"],
            "index": DomainIndex(lines),
            "lines": lines,
        })
    if len(remotes) != meta["runtime_remote_count"]:
        raise ValueError("beta remote source count drift")
    return meta, local, remotes


def trace(host: str, local, remotes, disable_ads=False, *, country=None):
    host = host.lower().rstrip(".")
    if not re.fullmatch(r"[a-z0-9.-]+", host) or not host or "." not in host:
        raise ValueError("host must be a plain non-private test hostname")
    for rule, policy in local:
        if naive_domain_match(host, rule):
            return {"policy": policy, "source": "local", "rule": rule}
    # Pinned diagnostics plugin has no routing [Rule]; additional user plugins
    # cannot be simulated here.
    for item in remotes:
        if disable_ads and item["policy"] == "AdBlock":
            continue
        matched = item["index"].match(host, country)
        if matched:
            return {"policy": item["policy"], "source": "remote",
                    "tag": item["tag"], "rule": matched,
                    'needs_geoip': country is None and condition(matched) is not None}
    # This is a domain-only prediction. Pure IPv4/IPv6 literal targets, SNI,
    # GEOIP,no-resolve and DNS are explicitly not included in this trace.
    return {"policy": "Final", "source": "fallback", "rule": "FINAL,Final"}


def report(root: Path = ROOT):
    meta, local, remotes = build(root)
    verified = {}
    for host, (active, disabled) in EXPECTED.items():
        on = trace(host, local, remotes)
        off = trace(host, local, remotes, True)
        if (on["policy"], off["policy"]) != (active, disabled):
            raise ValueError("domain route regression: " + host + " expected "
                             + repr((active, disabled)) + " got "
                             + repr((on["policy"], off["policy"])))
        verified[host] = {"adblock_on": on, "loon_adblock_disabled": off}
    pending = {host: {
        "actual_offline": trace(host, local, remotes),
        "review_reason": reason, "device_verification": "NOT_TESTED"
    } for host, reason in PENDING.items()}
    regional = {}
    for host,owner in REGIONAL.items():
        regional[host] = {}
        for country,expected in [('CN','DIRECT'),('US',owner)]:
            actual=trace(host,local,remotes,country=country)
            if actual['policy'] != expected:
                raise ValueError('regional route regression: ' + host + ' ' + country)
            regional[host][country]=actual
    return {
        "schema_version": 1, "status": "DOMAIN_ONLY_STATIC_ANALYSIS_NOT_DEVICE_OBSERVATION",
        "candidate": meta["version"],
        "configuration_sha256": meta["configuration_sha256"],
        "remote_subscriptions": len(remotes),
        "plugin_rules": 0,
        "adblock_disabled_means": "Beta-AdBlock-Balanced remote resource toggled off",
        "verified_synthetic_routes": verified,
        "regional_cases": regional,
        "open_scope_review": pending,
        "limitations": [
            "Rules in user's separately installed plugins, overrides or DNS filters are not included.",
            "Selected policy groups are names only; node region and performance are unknown.",
            "Domain matcher index cannot simulate SNI/ECH, DNS, GEOIP, IP-ASN, or CDN IP region.",
            "Matcher details within the same remote policy are shown by specificity, not necessarily Loon exact internal priority.",
            "All results are static offline route predictions, NOT real network traffic."
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    info = report()
    target = args.output.resolve()
    if target.is_relative_to(ROOT.resolve()):
        raise ValueError("reports should be written outside the tracked checkout")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(info, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps({"status": info["status"], "verified_cases": len(EXPECTED),
                      "pending_scopes": len(PENDING)}, sort_keys=True))


if __name__ == "__main__":
    main()
