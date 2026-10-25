"""Real-profile counterexamples for the routing and maintenance audit."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import beta_channel
import beta_cleanup
import reviewed_release
from route_diagnostics import Router


class AuditFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router()

    def owner(self, host):
        return self.router.match(host)['predicted_policy'].split(' (')[0]

    def test_shared_cloud_and_consent_hosts_do_not_inherit_unrelated_service(self):
        expected = {
            'ec2.us-west-2.amazonaws.com':'Final', 's3.us-west-2.amazonaws.com':'Final',
            'bedrock.us-west-2.amazonaws.com':'Final', 'sts.us-west-2.amazonaws.com':'Final',
            'cdn.cookielaw.org':'Final', 'www.onetrust.com':'Final',
            'disney-portal.my.onetrust.com':'Disney', 'e16991.b.akamaiedge.net':'Apple',
            'audit-only.azurewebsites.net':'Final', 'audit-only.azurefd.net':'Final',
            'audit-only.b.akamaiedge.net':'Final', 'audit-only.azurecosmosdb.com':'Final',
            'player.live-video.net':'Final', 'www.netflix.com':'Netflix',
            'www.microsoft.com':'Microsoft', 'www.twitch.tv':'Twitch',
        }
        for host, policy in expected.items():
            with self.subTest(host=host):
                self.assertEqual(self.owner(host), policy)

    def test_keyword_lookalikes_are_not_direct_and_known_service_endpoints_remain(self):
        for host in ['testflight.docs.example.test', 'buy.itunes.apple.com.audit-only.example.test',
                     'skydrive-notes.example.test', 'steamstore.docs.example.test',
                     'dualstack.apiproxy-audit-only.example.test']:
            self.assertEqual(self.owner(host),'Final',host)
        for host, owner in {'testflight.apple.com':'Apple', 'skydrive.live.com':'Microsoft',
                            'steamstore-a.akamaihd.net':'Steam', 'steambroadcast.akamaized.net':'Steam',
                            'www.musical.ly':'TikTok', 'nicegram.app':'Telegram'}.items():
            self.assertEqual(self.owner(host),owner,host)

    def test_netflix_ip_owner_uses_only_published_netflix_asns(self):
        entry = next(r for r in json.loads((ROOT/'build/release_manifest.json').read_text())['runtime_resources'] if r['tag']=='Our-Netflix')
        rules = beta_channel.content_rules((ROOT/entry['path']).read_bytes())
        self.assertEqual({r for r in rules if r.startswith('IP-ASN,')}, {'IP-ASN,2906,no-resolve','IP-ASN,40027,no-resolve'})
        self.assertFalse(any(r.startswith(('IP-CIDR,','IP-CIDR6,','DOMAIN-KEYWORD,')) for r in rules))
        self.assertEqual(self.owner('52.0.1.1'),'Final')

    def test_functional_push_is_allowed_and_precise_analytics_is_blocked(self):
        for host in ['cdn.onesignal.com','onesignal.com','challenges.cloudflare.com','ocsp.godaddy.com']:
            self.assertNotEqual(self.owner(host),'AdBlock',host)
        for host in ['static.cloudflareinsights.com','analytics.spotify.com','events.statsigapi.net']:
            self.assertEqual(self.owner(host),'AdBlock',host)

    def test_protected_general_and_geoip_are_byte_identical(self):
        old = (ROOT/'build/baselines/v6.5.6/LoonKit.lcf').read_text()
        new = (ROOT/'LoonKit.lcf').read_text()
        for name in ['General','Rule','Plugin','Remote Filter']:
            clean=lambda text:[x for x in beta_channel.section(text,name).splitlines() if x.strip() and not x.lstrip().startswith('#')]
            old_lines, new_lines = clean(old), clean(new)
            if name == 'General':
                # v6.5.10 intentionally changes only node latency probe URL.
                # Keep all other DNS, TUN and connectivity directives identical.
                self.assertEqual([l for l in old_lines if not l.startswith('proxy-test-url = ')],
                                 [l for l in new_lines if not l.startswith('proxy-test-url = ')])
                self.assertIn('proxy-test-url = http://www.bing.com', new_lines)
            elif name == 'Rule':
                # Gemini and GitHub Copilot have reviewed, service-specific local overrides.
                self.assertEqual(
                    old_lines,
                    [l.replace('DOMAIN,gemini.google.com,Gemini','DOMAIN,gemini.google.com,AI')
                      .replace('DOMAIN,aistudio.google.com,Gemini','DOMAIN,aistudio.google.com,AI')
                     for l in new_lines if l not in {
                       'DOMAIN,copilot-proxy.githubusercontent.com,AI',
                       'DOMAIN,copilot-telemetry-service.githubusercontent.com,AI',
                       'DOMAIN,copilot-telemetry.githubusercontent.com,AI',
                       'DOMAIN,copilot-workspace.githubnext.com,AI',
                       'DOMAIN,trae-api-sg.mchost.guru,AI',
                       'DOMAIN,trae-api-us.mchost.guru,AI',
                     }],
                    name)
                self.assertEqual(sum(x == 'GEOIP,CN,DIRECT,no-resolve' for x in new_lines),1)
                self.assertEqual(new_lines[-1], 'FINAL,Final')
            elif name == 'Plugin':
                spec=json.loads((ROOT/'build/release_spec.json').read_text())
                expected=('https://raw.githubusercontent.com/YohakuSama/loonkit/'
                          +spec['plugin_assets_commit']+'/release/Network_Diagnostics.plugin, enabled=true')
                self.assertEqual(new_lines,[expected])
                self.assertEqual(len(old_lines),1)
            else:
                self.assertEqual(old_lines, new_lines, name)
        self.assertIn('GEOIP,CN,DIRECT,no-resolve',new)
        self.assertIn('dns-reject-mode = LOOPBACKIP',new)

    def test_public_cli_uses_the_real_formal_profile(self):
        for args in [('match','open.spotify.com'),('coverage',),('audit',)]:
            result = subprocess.run([sys.executable,'scripts/route_diagnostics.py',*args,'--json'],cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            payload = json.loads(result.stdout)
            if args[0]=='match': self.assertEqual(payload['predicted_policy'],'Spotify')
            if args[0]=='coverage': self.assertTrue(payload['all_reviewed_roots_match'])

    def test_beta_foundation_manifest_tampering_is_rejected(self):
        meta=json.loads((ROOT/'build/beta_manifest.json').read_text())
        path=ROOT/meta['foundation_manifest_path']
        read=Path.read_bytes
        with patch.object(Path,'read_bytes',lambda p: read(p)+b' ' if p==path else read(p)):
            with self.assertRaisesRegex(ValueError,'foundation manifest'):
                beta_channel.validate()

    def test_reviewed_asset_corruption_is_rejected_by_real_router(self):
        meta=json.loads((ROOT/'build/release_manifest.json').read_text())
        target=ROOT/next(r['path'] for r in meta['runtime_resources'] if r['tag']=='Our-Netflix')
        read = Path.read_bytes
        def damaged(path):
            raw = read(path)
            return raw+b'DOMAIN,unreviewed.example.test\n' if path==target else raw
        with patch.object(Path,'read_bytes',damaged):
            with self.assertRaisesRegex(ValueError,'manifest'):
                Router()

    def test_cleanup_protects_config_only_resource_and_later_formal_version(self):
        from test_beta_cleanup import BetaCleanupTests
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            path,raw,archive=BetaCleanupTests().fixture(root)
            profile=('# LoonKit v1.0.1\n[Remote Rule]\n'+archive['uri']+', policy=Proxy, tag=ConfigOnly, enabled=true\n').encode()
            (root/'LoonKit.lcf').write_bytes(profile)
            meta=json.loads((root/'build/release_manifest.json').read_text())
            meta['label']='v1.0.1'
            meta['profile_sha256']['LoonKit.lcf']=hashlib.sha256(profile).hexdigest()
            (root/'build/release_manifest.json').write_text(json.dumps(meta))
            plan=beta_cleanup.inventory(root)
            self.assertEqual(plan['status'],'READY_FOR_ARCHIVAL_VERIFICATION')
            self.assertNotIn(str(path.relative_to(root)),[r['path'] for r in plan['candidates']])
            self.assertGreaterEqual(plan['current_resources_protected'],3)
