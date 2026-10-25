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

    def test_cn_and_overseas_domains_have_distinct_routes(self):
        owners={'www.apple.com':'Apple','configuration.apple.com':'Apple','crl.microsoft.com':'Microsoft',
                'download.microsoft.com':'Microsoft','www.paypal.com':'Paypal','www.bilibili.com':'Bilibili',
                'cn.bing.com':'Microsoft'}
        for host,owner in owners.items():
            for country,expected in [('CN','DIRECT'),('US',owner),('JP',owner)]:
                with self.subTest(host=host,country=country):
                    self.assertEqual(self.router.match(host,country=country)['predicted_policy'],expected)
                    self.assertEqual(audit.trace(host,self.local,self.remotes,country=country)['policy'],expected)

    def test_privacy_and_ai_overrides_keep_precedence(self):
        for country in ('CN','US'):
            for host,owner in [('telemetry.microsoft.com','AdBlock'),('copilot.microsoft.com','AI'),('analytics.spotify.com','AdBlock')]:
                self.assertEqual(self.router.match(host,country=country)['predicted_policy'],owner)
            self.assertEqual(audit.trace('telemetry.microsoft.com',self.local,self.remotes,True,country=country)['policy'],'DIRECT' if country=='CN' else 'Microsoft')

    def test_unknown_geography_is_explicit_and_does_not_pretend_direct(self):
        result=self.router.match('www.apple.com')
        self.assertEqual(result['prediction_status'],'NEEDS_GEOIP')
        self.assertEqual(result['regional_options'],{'CN':'DIRECT','otherwise':'Apple'})
        for host in ('www.netflix.com','example.invalid','cdn.onesignal.com'):
            self.assertNotEqual(self.router.match(host)['prediction_status'],'NEEDS_GEOIP')

    def test_suffix_boundaries_and_shared_cdn_do_not_inherit_a_service(self):
        for host in ('apple.com.example.test','microsoft.com.example.test','bilibili.com.example.test','paypal.com.example.test'):
            for country in ('CN','US'):
                self.assertTrue(self.router.match(host,country=country)['predicted_policy'].startswith('Final'))
        for host in ('tenant.kunlunhuf.com','tenant.ksyungslb.com'):
            self.assertEqual(self.router.match(host,country='CN')['predicted_policy'],'DIRECT')
            self.assertTrue(self.router.match(host,country='US')['predicted_policy'].startswith('Final'))

    def test_literal_ipv4_ipv6_and_asn_conditions(self):
        meta=json.loads((ROOT/'build/release_manifest.json').read_text())
        rows=next(r for r in meta['runtime_resources'] if r['tag']=='Our-Apple')
        import ipaddress
        for kind in ('IP-CIDR','IP-CIDR6'):
            child=next(condition(r)[0] for r in content_rules((ROOT/rows['path']).read_bytes()) if condition(r)[0].startswith(kind+','))
            address=str(ipaddress.ip_network(child.split(',')[1]).network_address)
            self.assertEqual(self.router.match(address,country='CN')['predicted_policy'],'DIRECT')
            self.assertEqual(self.router.match(address,country='US')['predicted_policy'],'Apple')
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

    def test_removed_unconditional_direct_entries_keep_cn_coverage(self):
        recipe=json.loads((ROOT/'rules/reviewed/v6.5.8/decisions.json').read_text())
        for row in recipe['rules']:
            if row['owner'] != 'DIRECT':continue
            for rule in row['remove_exact']:
                host=rule.split(',')[1]
                for sample in [host]+(['regional-check.'+host] if rule.startswith('DOMAIN-SUFFIX,') else []):
                    self.assertIn(self.router.match(sample,country='CN')['predicted_policy'],{'DIRECT','AdBlock'},sample)
        self.assertEqual(self.router.match('servicewechat.com',country='CN')['predicted_policy'],'DIRECT')
        self.assertTrue(self.router.match('servicewechat.com',country='US')['predicted_policy'].startswith('Final'))
        self.assertTrue(self.router.match('wechat.com',country='CN')['predicted_policy'].startswith('Final'))

    def test_review_baselines_use_all_actual_groups_and_underlying_matchers(self):
        formal=upstream_review.runtime_baseline(ROOT)
        beta=upstream_review.runtime_baseline(ROOT,profile_path='beta/LoonKit.lcf',manifest_path='build/beta_manifest.json')
        self.assertEqual(formal,beta)
        self.assertEqual(len(formal),33)
        self.assertIn('DOMAIN-SUFFIX,apple.com',formal['Apple'])
        self.assertFalse(any(r.startswith('AND,') for group in formal.values() for r in group))

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
