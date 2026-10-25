"""Independent scenario expectations for the actual regional resources."""
import json
from pathlib import Path
import re
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from route_diagnostics import Router
import beta_effective_audit as audit
from beta_channel import content_rules
from regional_rules import condition
import upstream_review


class RegionalRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router=Router()
        cls.meta,cls.local,cls.remotes=audit.build()

    def test_native_domains_are_stable_owner_matches_without_geoip_composites(self):
        # v6.5.9 intentionally gives up same-host CN/non-CN dynamic routing to
        # prevent actual rule-hit VPN crashes caused by nested AND+GEOIP.
        owners={'www.apple.com':'Apple','configuration.apple.com':'Apple',
                'crl.microsoft.com':'Microsoft','download.microsoft.com':'Microsoft',
                'www.paypal.com':'Paypal','www.bilibili.com':'Bilibili',
                'cn.bing.com':'Microsoft'}
        for host,owner in owners.items():
            for country in (None,'CN','US','JP'):
                with self.subTest(host=host,country=country):
                    self.assertEqual(self.router.match(host,country=country)['predicted_policy'],owner)
                    self.assertEqual(audit.trace(host,self.local,self.remotes,country=country)['policy'],owner)

    def test_privacy_and_ai_overrides_keep_precedence(self):
        for country in ('CN','US'):
            for host,owner in [('telemetry.microsoft.com','AdBlock'),('copilot.microsoft.com','AI'),('analytics.spotify.com','AdBlock')]:
                self.assertEqual(self.router.match(host,country=country)['predicted_policy'],owner)
            self.assertEqual(audit.trace('telemetry.microsoft.com',self.local,self.remotes,True,country=country)['policy'],'DIRECT' if country=='CN' else 'Microsoft')

    def test_unknown_geography_uses_native_service_match_without_faking_cn_direct(self):
        result=self.router.match('www.apple.com')
        self.assertEqual(result['prediction_status'],'MATCHED')
        self.assertEqual(result['predicted_policy'],'Apple')
        self.assertIsNone(result['regional_options'])
        for host in ('www.netflix.com','example.invalid','cdn.onesignal.com'):
            self.assertNotEqual(self.router.match(host)['prediction_status'],'NEEDS_GEOIP')

    def test_suffix_boundaries_and_shared_cdn_do_not_inherit_a_service(self):
        for host in ('apple.com.example.test','microsoft.com.example.test','bilibili.com.example.test','paypal.com.example.test'):
            for country in ('CN','US'):
                self.assertTrue(self.router.match(host,country=country)['predicted_policy'].startswith('Final'))
        # Previous RegionalCN directly caught generic shared CDN roots.
        # That remote is now removed as a redundant/high-risk GEOIP composite.
        # No new broad DOMAIN-SUFFIX DIRECT exception may replace it.
        for host in ('tenant.kunlunhuf.com','tenant.ksyungslb.com'):
            for country in ('CN','US'):
                self.assertTrue(self.router.match(host,country=country)['predicted_policy'].startswith('Final'))

    def test_native_service_rules_do_not_proxy_former_foreign_only_ip_slices(self):
        import ipaddress
        original=(ROOT/'rules/releases/v6.5.8/Apple.list').read_bytes()
        archived_ip=[condition(rule)[0] for rule in content_rules(original)
                     if condition(rule) is not None
                     and condition(rule)[0].startswith(('IP-CIDR,','IP-CIDR6,'))]
        self.assertEqual(len(archived_ip),13)
        meta=json.loads((ROOT/'build/release_manifest.json').read_text())
        active=next(row for row in meta['runtime_resources'] if row['tag']=='Our-Apple')
        current=content_rules((ROOT/active['path']).read_bytes())
        self.assertFalse(any(x.startswith(('IP-CIDR,','IP-CIDR6,','AND,','OR,','NOT,'))
                             for x in current))
        for original_rule in archived_ip:
            address=str(ipaddress.ip_network(original_rule.split(',')[1]).network_address)
            self.assertNotEqual(
                self.router.match(address,country='US')['predicted_policy'],'Apple')
        for asn in (2906,40027):
            self.assertEqual(self.router.match('45.57.0.1',country='US',asn=asn)['predicted_policy'],'Netflix')
        self.assertTrue(self.router.match('45.57.0.1',country='US',asn=8075)['predicted_policy'].startswith('Final'))
        self.assertEqual(self.router.match('203.1.1.1',country='CN')['predicted_policy'],'DIRECT')
        self.assertTrue(self.router.match('unregistered.example',country='CN')['predicted_policy'].startswith('Final'))

    def test_no_active_ua_or_keywords_and_overseas_groups_have_no_direct_option(self):
        meta=json.loads((ROOT/'build/release_manifest.json').read_text())
        for row in meta['runtime_resources']:
            self.assertFalse(any(r.startswith(('USER-AGENT,','DOMAIN-KEYWORD,')) for r in content_rules((ROOT/row['path']).read_bytes())))
        text=(ROOT/'LoonKit.lcf').read_text()
        for group in ('Apple','Microsoft','Paypal','Bilibili'):
            line=re.search(r'(?m)^'+group+r' = (.*)$',text)[1].split('img-url',1)[0]
            self.assertEqual(line,'select,Proxy,Auto,Fallback,ALL_Filter,')

    def test_removed_regional_cn_scope_does_not_reintroduce_blanket_direct(self):
        # The high-risk RegionalCN subscription is entirely gone from active
        # profile, and the local no-resolve GEOIP fallback is still present.
        content=(ROOT/'LoonKit.lcf').read_text()
        self.assertNotIn('tag=Our-RegionalCN,',content)
        self.assertIn('GEOIP,CN,DIRECT,no-resolve',content)
        self.assertIn('FINAL,Final',content)
        for host in ('autonavi.com','tenant.ksyungslb.com','tenant.kunlunhuf.com'):
            for country in ('CN','US'):
                self.assertTrue(self.router.match(host,country=country)['predicted_policy'].startswith('Final'))

    def test_review_baseline_is_native_only_with_beta_still_historical(self):
        formal=upstream_review.runtime_baseline(ROOT)
        beta=upstream_review.runtime_baseline(
            ROOT,profile_path='beta/LoonKit.lcf',manifest_path='build/beta_manifest.json')
        self.assertEqual(len(formal),33)
        self.assertEqual(set(formal),set(beta))
        self.assertIn('DOMAIN-SUFFIX,apple.com',formal['Apple'])
        self.assertFalse(any(r.startswith(('AND,','OR,','NOT,'))
                             for group in formal.values() for r in group))
        self.assertTrue(all(x.startswith(('DOMAIN,','DOMAIN-SUFFIX,'))
                            for x in formal['Apple']))
        # Explicit, traceable intentional differences: former conditional IP
        # sub-rules are excluded, rather than routed without GEOIP checks.
        self.assertEqual(len(beta['Apple']-formal['Apple']),13)
        self.assertEqual(len(beta['Bilibili']-formal['Bilibili']),8)
        for group in formal:
            if group not in ('Apple','Bilibili'):
                self.assertEqual(formal[group],beta[group],group)

    def test_upstream_plan_cannot_shadow_cn_only_scopes(self):
        from beta_upstream_delivery import effective_conflict
        for host in ('servicewechat.com','new.autonavi.com','tenant.kunlunhuf.com'):
            self.assertEqual(effective_conflict(host,'YouTube',self.local,self.remotes),'REGIONAL_SCOPE_REVIEW')
        self.assertIsNone(effective_conflict('unreviewed.example.test','YouTube',self.local,self.remotes))

    def test_alidns_tls_hostname_and_bootstrap_are_preserved(self):
        text=(ROOT/'LoonKit.lcf').read_text()
        self.assertIn('doh-server = https://dns.alidns.com/dns-query',text)
        self.assertIn('[Host]\ndns.alidns.com = 223.5.5.5',text)
        self.assertNotIn('https://223.5.5.5/',text)
        self.assertNotIn('skip-server-cert-verify',text)


if __name__=='__main__':unittest.main()
