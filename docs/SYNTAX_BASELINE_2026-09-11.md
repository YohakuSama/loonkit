# Loon 2026-09-11 syntax audit — historical beta snapshot

> Historical evidence recorded on 2026-09-11. References to production v6.5.4, beta v6.5.5-beta.2 and the seven-day gate describe the state **at that date**, not the current main branch. For current configuration and user instructions, see [LoonKit.lcf](../LoonKit.lcf) and [DNS guide](./DNS_PRIVACY.md).

Status: **documented / CI contract tests / actual Loon runtime NOT tested**.
This audit makes **no runtime configuration changes**. Keep production main v6.5.4,
beta v6.5.5-beta.2, AliDNS, all pinned rules and the current 7-day device gate.

## Reference order and provenance

1. Official 2026 example: [LoonExampleConfig/example2.lcf](https://github.com/Loon0x00/LoonExampleConfig/blob/f5b97c72dfe35283678c6da68b21c959ff30126d/example2.lcf), repository commit `f5b97c72dfe35283678c6da68b21c959ff30126d`, file Git blob `1a3bd778974c2dfe11a49e26b667ca10c790fb0b`, header updated **2026-09-11**.
2. Official current manuals: [Rule](https://nsloon.app/docs/Rule/), [IP/no-resolve](https://nsloon.app/docs/Rule/ip_rule/), [General](https://nsloon.app/docs/General/), [DNS](https://nsloon.app/docs/DNS/), [Node](https://nsloon.app/docs/Node/), [Plugin](https://nsloon.app/docs/Plugin/).
3. Historical archived Loon knowledge-base (material supplied by maintainer; original article dated **2024-11-26**, Wayback capture 2025-03-08) is useful only to distinguish legacy behavior. It is **not** the latest syntax specification.
4. Real Loon device observation overrides assumptions about app UI, effective request route, DNS transport and version compatibility, but is never silently presented as documentation.

**Another documentation-version difference:** The 2026-09-11 example lists `v4-only` / `prefer-v4` / `prefer-v6` / `v6-only` for `ip-mode`, whereas the currently crawled online General page also displays legacy-looking `ipv4-only` / `ipv4-preferred` / `ipv6-preferred`. We leave the unambiguous, already-deployed `ip-mode=dual` unchanged, and treat other mode spellings as requiring a current Loon Build validation before adoption.

**Conflict in supplied copy:** a separately pasted copy labelled 2026-09-11 described the DoQ default port as `853`. The Loon-maintained same-date `example2.lcf` and current online manual say `784`. Use the official upstream version as the documentation baseline for default claims; explicit `quic://server:port` must use the actual provider port. LoonKit config intentionally has **no DoQ**, so no DoQ port is introduced in this audit.

## Compatibility map

| Current capability | 2026 official sample | Beta assessment and decision |
| --- | --- | --- |
| English `[General]`, `[Proxy]`, `[Rule]`, `[Remote Rule]`, `[Plugin]` | Named sections are English | Already correct. Their display order in a sample does not by itself establish a mandatory on-disk order; preserve working beta arrangement. |
| `dns-server`, `doh-server`, `hijack-dns`, `ip-mode=dual` | Supported; DNS supports DoQ and DoH3 too | AliDNS remains `223.5.5.5,223.6.6.6` and `https://dns.alidns.com/dns-query`. Do not add `system`, Google DNS, DoQ or DoH3 just to match a demonstration. |
| `udp-fallback-mode` | `DIRECT` in example | Retain beta's `REJECT`: it is **UDP proxy capability fallback**, not encrypted-DNS-failure fallback. |
| `GEOIP,CN,DIRECT,no-resolve` | `GEOIP` plus valid `no-resolve` examples in official manuals | Deliberate privacy/performance compromise: only available target IP is evaluated; unknown mainland domain may fall into `Final`. Archived advice to omit no-resolve targets a different completeness goal and must not silently reverse this decision. |
| `DOMAIN`, `DOMAIN-SUFFIX`, `IP-CIDR`, `IP-ASN` | Still supported | Keep policy-source precedence **local > plugin > remote** and domain matching before DNS-triggered IP matching. |
| `DEST-PORT`, `PROTOCOL`, `AND`/logic rules | Demonstrated in new example | **Supported by Loon but not by our current 7-type offline rules compiler.** Leave fail-closed parser rejection and add focused tests rather than falsely declaring Loon unsupported or lossy-converting them. Extend compiler only with separate semantic/matching tests before ingesting such upstream expressions. |
| `[Rewrite]` / `[Script]` expressive conditions and pipes | Modern expression syntax; older syntax remains readable | Main LoonKit config has no new Rewrite or direct Script sections. Pinned diagnostics plugin already uses `generic then script(...)` and `network-changed then script(...)`. Do not bulk-rewrite an unrelated working plugin merely because samples changed. Plugin argument interpolation still needs Loon-device verification. |
| Plugin `pin`, tag, policy, enable | New example shows optional `pin` and `policy` | Plugin/script URLs already reference immutable Git commits. Do not attach mutable default-branch demonstration plugins. UI `pin` is not a replacement for reviewing actual content SHA. |
| `ssid-trigger` and `ssid` strategy | Both valid options | Do not copy demo SSID global DIRECT triggers; they can bypass effective REJECT rules. No global mode switch added to beta. |
| `disable-stun`, `sni-sniffing`, `real-ip` | Supported | Beta.2 explicitly tests `sni-sniffing=true` for IP-target TLS routing. `disable-stun=true` and `real-ip` remain unchanged. No blanket new MITM/IPv6/QUIC changes; compare real-device routing and revert if important misclassification occurs. |
| Nodes (WireGuard, Hysteria2, Reality, AnyTLS, QUIC) | Illustrative example credentials | No sample nodes, passwords or parser placeholders are copied into shared profiles. Personal subscriptions remain local; preserve manual node selection. |
| `[Host]` and per-SSID DNS override | Demonstrated | Absent from LoonKit public beta; do not inject bypass resolvers or host overrides just to mirror the example. |
| `[MITM]` certificate and private CA | Optional example | Do not install certificates, skip TLS checks or force MITM globally. HTTPS URL-level rewrites require legitimate MITM prerequisites and individual test evidence. |

## Priority and DNS privacy facts (2026 docs)

- Request rule resolution: domain rules first for domain targets; only unresolved domains continue to DNS/IP classes; the current official source order is **local > plugin > remote**. A local Microsoft/Facebook parent root can shadow remote AdBlock domain matchers, so this beta's removal has a real priority rationale.
- `DIRECT` means bypass the proxy; changing a REJECT policy group's child to DIRECT **does not** resume matching. Disable **both** relevant remote AdBlock subscriptions for Loon-side disable tests. Independent DNS/cloud filters are not controlled by that toggle.
- `no-resolve` avoids DNS for IP rules on domain targets. It does not prove complete mainland coverage.
- When plain and encrypted DNS coexist, Loon prefers encrypted DNS but uses concurrent queries over configured valid servers; **on encrypted-DNS failure it defaults to ordinary DNS fallback unless disabled in the App DNS settings**. `udp-fallback-mode=REJECT` is not an encrypted-DNS fallback switch.
- `hijack-dns=*:53` intercepts UDP DNS to port 53, **not all application DoH/DoT, TCP/53, IPv6 or paths bypassing Loon**. A no-leak statement requires packet-path tests and failure injection.

## Required regression and release gating

- CI: `python3 -m unittest discover -s tests -p 'test_*.py' -v`, including `test_syntax_baseline_2026.py`.
- App: verify actual Loon Build (**diagnostics plugin declares 3.5.1(983)**), resource refresh, Airplane/Wi-Fi/cellular switch, DNS fail-closed toggle, DoH failure, node failure, IPv4/IPv6, protocol handling and real services against the beta matrix.
- Comparison result **NOT_TESTED_ON_DEVICE**. Do not promote beta to main or delete previous immutable resources based solely on documentation parity.
