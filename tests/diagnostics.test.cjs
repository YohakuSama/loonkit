// Offline Loon API doubles: no actual requests, no change to production probe logic.
'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const published = require('./helpers/diagnostics.cjs');
const SCRIPTS = {
  node: 'node-intelligence.js',
  network: 'network-diagnostics.js',
  media: 'media-unlock.js'
};

function run(kind, handler, options = {}) {
  const requests = [], completed = [], timers = [], alerts = [], writes = [];
  const http = (method, request, callback) => {
    requests.push({method, request, callback});
    const reply = handler({method, request, index: requests.length - 1});
    if (reply && reply.hold) return;
    callback(reply && reply.error || null,
      reply && reply.response || {status: reply && reply.status !== undefined ? reply.status : 200,
                                  headers: reply && reply.headers || {}},
      reply && reply.body !== undefined ? reply.body : '');
  };
  const dns = options.dns === null ? undefined : {
    query(request, callback) {
      const result = options.dns || {
        reply: {answers: [{type:'A', value:'203.0.113.1'}],
                protocol: 'doh', server: 'https://dns.example/dns-query'}
      };
      if (result.throwError) throw new Error('bad native dns API');
      callback(result.error || null, result.reply);
    }
  };
  const sandbox = {
    $argument: options.argument || {target_policy:'Node-A'},
    $environment: {params: options.params || {node: 'Node-A'}},
    $script: {name: '手动检测'},
    $config: options.config,
    $httpClient: {
      get(request, callback) {return http('GET', request, callback);},
      post(request, callback) {return http('POST', request, callback);}
    },
    $dns: dns,
    $done(value) {completed.push(value);},
    $persistentStore: {
      read() {return null;},
      write(value, key) {writes.push({value,key});}
    },
    $notification: {post(...args) {alerts.push(args);}},
    setTimeout(fn, delay) {
      timers.push({fn, delay});
      if(delay<=350)fn();
      return timers.length;
    }
  };
  const src = published.source(SCRIPTS[kind]);
  vm.runInNewContext(src, sandbox, {timeout:3000, filename:SCRIPTS[kind]});
  return {requests, completed, timers, alerts, writes};
}
const output = session => String(session.completed[0] && session.completed[0].content || '');

const SINGLE = 'https://ipconfig.is/json';
function richNode(ip = '8.8.8.8') {
  return JSON.stringify({
    ip, city:'Mountain View',region:'California',country_name:'United States',
    country_code:'US',org:'Google LLC',asn:'AS15169 Google LLC',asn_number:15169,
    network:'8.8.8.0/24',ptr_record:'dns.google',timezone:'America/Los_Angeles',
    latitude:37.423,longitude:-122.083,accuracy_radius:35,
    is_hosting:true,is_mobile:false,is_vpn:false,is_tor:false
  });
}
test('node: one source returns the full actual egress record, not a stripped display', () => {
  const s=run('node',()=>({status:200,body:richNode()}));
  assert.equal(s.requests.length,1);
  assert.equal(s.requests[0].request.url,SINGLE);
  assert.equal(s.requests[0].request.node,'Node-A');
  assert.equal(s.requests[0].request['auto-redirect'],false);
  assert.equal(s.requests[0].request['auto-cookie'],false);
  const o=output(s);
  for (const text of ['出口 IP：8.8.8.8','IP 版本：IPv4','United States (US)',
    'California','Mountain View','运营商：Google LLC','ASN：AS15169 Google LLC',
    'IP 网段：8.8.8.0/24','反向 DNS：dns.google','时区：America/Los_Angeles',
    '估算坐标：37.4230, -122.0830','定位半径：35 km',
    '机房 / 云：检出','移动网络：未检出','VPN / 代理：未检出',
    'Tor：未检出','数据源：ipconfig.is'])assert.ok(o.includes(text),text);
  assert.doesNotMatch(o,/风险评分|住宅 IP|家宽判定/);
  assert.equal(s.completed.length,1);
});
test('node: native nodeInfo is labeled as entry, not inferred as egress',()=>{
  const s=run('node',()=>({status:200,body:richNode()}),{
    params:{node:'Old-Node',nodeInfo:{name:'Selected-Node',type:'hysteria2',
      server:'entry.example.net',port:443}},
    argument:{target_policy:'Proxy'}});
  assert.equal(s.requests.length,1);
  assert.equal(s.requests[0].request.node,'Selected-Node');
  assert.match(output(s),/节点：Selected-Node/);
  assert.match(output(s),/协议：hysteria2/);
  assert.match(output(s),/入口：entry\.example\.net:443/);
  assert.match(output(s),/出口 IP：8\.8\.8\.8/);
});
test('node: missing third-party metadata remains unknown, not guessed',()=>{
  const s=run('node',()=>({status:200,body:JSON.stringify({ip:'8.8.8.8'})}));
  assert.match(output(s),/运营商：未知/);
  assert.match(output(s),/ASN：未知/);
  assert.match(output(s),/机房 \/ 云：未知/);
  assert.equal(s.requests.length,1);
});
test('node: redirects, bad JSON, errors and rate limits are visible failures',()=>{
  for(const value of [
    {status:302},{status:429},{status:200,body:'{'},{error:new Error('timeout')},
    {status:200,body:'{"ip":"not-an-ip"}'}, {throws:true}
  ]){
    const s=run('node',()=>{
      if(value.throws)throw Error('request exception');
      return value;
    });
    assert.equal(s.requests.length,value.error||value.throws?2:1);
    assert.match(output(s),/出口信息查询失败/);
    assert.doesNotMatch(output(s),/出口 IP：8\.8\.8\.8/);
    assert.equal(s.completed.length,1);
  }
});
test('node: policy group resolves to named node, unknown defaults make zero requests',()=>{
  const s=run('node',()=>({status:200,body:richNode()}),{
    params:{},argument:{target_policy:'Proxy'},
    config:{getConfig(){return JSON.stringify({all_policy_groups:['Proxy']});},
      getSelectedPolicy(p){return p==='Proxy'?'Node-C':'';}}
  });
  assert.equal(s.requests[0].request.node,'Node-C');
  const fail=run('node',()=>({status:200,body:richNode()}),{params:{},argument:{target_policy:'Proxy'}});
  assert.equal(fail.requests.length,0);
  assert.match(output(fail),/无法确定选中节点/);
});
test('node: optional DIRECT comparison uses same source but distinct policies',()=>{
  const s=run('node',({request})=>({status:200,
    body:richNode(request.node==='DIRECT'?'1.1.1.1':'8.8.8.8')}),
    {argument:{target_policy:'Node-A',compare_direct:true}});
  assert.equal(s.requests.length,2);
  assert.ok(s.requests.every(x=>x.request.url===SINGLE));
  assert.equal(s.requests[0].request.node,'Node-A');
  assert.equal(s.requests[1].request.node,'DIRECT');
  assert.match(output(s),/直连出口：1\.1\.1\.1/);
  assert.match(output(s),/与节点出口：不同/);
});
test('node: silent HTTP hangs produce a single timeout completion',()=>{
  const s=run('node',()=>({hold:true}));
  assert.equal(s.completed.length,0);
  const timer=s.timers.find(t=>t.delay>=30000&&t.delay<80000);
  assert.ok(timer);
  timer.fn();
  assert.equal(s.completed.length,1);
  assert.match(output(s),/查询超时/);
});

function networkReply(request, status) {
  assert.equal(request['auto-redirect'], false);
  assert.equal(request['auto-cookie'], false);
  assert.equal(request.url, request.node === 'DIRECT' ?
    'http://wifi.vivo.com.cn/generate_204' : 'https://www.gstatic.com/generate_204');
  return {status};
}
test('network: HTTP 204 plus native DoH produces a successful manual summary', () => {
  const session = run('network', ({request}) => networkReply(request, 204));
  assert.equal(session.requests.length, 2);
  assert.equal(session.requests[0].request.node, 'DIRECT');
  assert.equal(session.requests[1].request.node, 'Node-A');
  assert.match(output(session), /连接正常/);
  assert.match(output(session), /解析成功 · DoH/);
  assert.equal(session.completed.length, 1);
});

test('network: redirects and captive-portal HTTP 200 stay uncertain, not success', () => {
  const session = run('network', ({request,index}) =>
    networkReply(request, index === 0 ? 302 : 200));
  assert.match(output(session), /待确认/);
  assert.match(output(session), /目标重定向/);
  assert.match(output(session), /网络认证/);
  assert.doesNotMatch(output(session), /结论：连接正常/);
});

test('network: timeout and malformed DNS evidence fail without false DoH claims', () => {
  const session = run('network', ({request}) =>
    request.node === 'DIRECT' ? {error:new Error('timeout')} : {status:204},
    {dns:{reply:{protocol:'doh', answers:[{type:'CNAME', value:'invalid'}]}}});
  assert.match(output(session), /结论：节点连接正常/);
  assert.match(output(session), /直连：失败/);
  assert.match(output(session), /超时/);
  assert.match(output(session), /没有获得有效的解析地址/);
  assert.doesNotMatch(output(session), /解析成功 · DoH/);
});

test('network: DNS exception and unsupported native API cannot be misreported as success', () => {
  const thrown = run('network', () => ({status:204}), {dns:{throwError:true}});
  assert.match(output(thrown), /DNS API 调用异常/);
  const missing = run('network', () => ({status:204}), {dns:null});
  assert.match(output(missing), /不支持 DNS 检测/);
  assert.match(output(missing), /结论：节点连接正常/);
});

test('network: manual detection makes no automatic requests or notifications', () => {
  const session = run('network', ({request}) => networkReply(request, 204));
  assert.equal(session.alerts.length, 0);
  assert.equal(session.writes.length, 0);
  assert.equal(session.requests.length, 2);
  assert.ok(session.requests.every(call => call.request.node === 'DIRECT' || call.request.node === 'Node-A'));
});

test('network: failed DIRECT and DNS do not imply the selected node failed', () => {
  const session = run('network', ({request}) =>
    request.node === 'DIRECT' ? {error: new Error('timeout')} : {status:204},
    {dns:{error:new Error('dns timeout')}});
  assert.match(output(session), /直连：失败/);
  assert.match(output(session), /DNS：失败/);
  assert.match(output(session), /结论：节点连接正常/);
});


function mediaResponse({method, request}) {
  const url = new URL(request.url);
  if (url.hostname === 'startup.core.indazn.com') return {status:200, body:JSON.stringify({GeolocatedCountry:'US'})};
  if (url.hostname === 'us1-prod-direct.discoveryplus.com' && url.pathname === '/token') return {status:200, body:JSON.stringify({data:{attributes:{token:'fake-test-token'}}})};
  if (url.hostname === 'www.paramountplus.com') return {status:200, body:'Paramount+'};
  if (url.hostname === 'disney.api.edge.bamgrid.com') return {status:200, body:JSON.stringify({extensions:{sdk:{session:{inSupportedLocation:true,location:{countryCode:'US'}}}}})};
  if (url.hostname === 'www.netflix.com' && url.pathname.startsWith('/title/')) return {status:200, body:'Netflix /title/81280792'};
  if (url.hostname === 'www.youtube.com' && url.pathname === '/premium') return {status:200, body:'{"GL":"US"}'};
  if (url.hostname === 'chatgpt.com' && url.pathname === '/cdn-cgi/trace') return {status:200, body:'loc=US\n'};
  if (url.href === 'https://chatgpt.com/') return {status:200, body:'ChatGPT OpenAI'};
  return {status:503};
}
test('media: seven mocked supported responses produce seven distinct verdicts', () => {
  const session = run('media', mediaResponse);
  assert.equal(session.completed.length, 1);
  const out = output(session);
  for (const name of ['DAZN','Discovery+','Paramount+','Disney+','Netflix','ChatGPT','YouTube Premium']) {
    assert.ok(out.includes(name + '　'), 'missing service result: ' + name);
  }
  assert.match(out, /✅ Netflix　片源可访问/);
  assert.match(out, /✅ Discovery\+　可访问/);
  assert.match(out, /✅ YouTube Premium　可用/);
  assert.match(out,/可访问：7 \/ 7/);
  assert.equal((out.match(/✅/g)||[]).length, 7);
  assert.doesNotMatch(out, /会员|已订阅|完整解锁/);
  assert.ok(session.requests.every(r => r.request.node === 'Node-A'));
  assert.ok(session.requests.length >= 8);
  assert.ok(session.requests.every(r => !r.request.url.includes('/users/me')));
  assert.ok(session.requests.filter(r => r.method === 'POST').length >= 2);
});

test('media: redirect-based block and Netflix 404 remain conservative', () => {
  const session = run('media', call => {
    if (new URL(call.request.url).hostname === 'www.paramountplus.com')
      return {status:302, headers:{location:'https://www.paramountplus.com/unavailable'}};
    if (new URL(call.request.url).hostname === 'www.netflix.com') return {status:404};
    if (call.request.url === 'https://chatgpt.com/')
      return {status:302, headers:{Location:'https://auth.openai.com/login'}};
    return mediaResponse(call);
  });
  assert.match(output(session), /⛔ Paramount\+　受限/);
  assert.match(output(session), /⚠️ Netflix　待确认/);
  assert.match(output(session), /✅ ChatGPT　可用/);
});

test('media: malformed platform JSON and thrown requests cannot create supported verdicts', () => {
  const session = run('media', call => {
    if (new URL(call.request.url).hostname === 'disney.api.edge.bamgrid.com') return {status:200, body:'{broken'};
    if (new URL(call.request.url).hostname === 'startup.core.indazn.com') throw new Error('request exception');
    return mediaResponse(call);
  });
  assert.match(output(session), /⚠️ DAZN　失败/);
  assert.match(output(session), /⚠️ Disney\+　失败/);
});

test('media: node context overrides a different configured fallback', () => {
  const session = run('media', mediaResponse,
    {params:{node:'Node-Menu'}, argument:{target_policy:'Node-Other'}});
  assert.ok(session.requests.every(x => x.request.node === 'Node-Menu'));
});

test('media: no concrete node means no service requests', () => {
  const session = run('media', mediaResponse,
    {params:{}, argument:{target_policy:'Proxy'}});
  assert.equal(session.requests.length, 0);
  assert.match(output(session), /指定具体节点/);
});

test('media: selected policy groups must resolve to a concrete node', () => {
  const session = run('media', mediaResponse, {
    params:{}, argument:{target_policy:'Proxy'},
    config:{
      getConfig(){return JSON.stringify({all_policy_groups:['Proxy','Auto']});},
      getSelectedPolicy(name){return {Proxy:'Auto',Auto:'Node-C'}[name]||'';}
    }
  });
  assert.ok(session.requests.length > 0);
  assert.ok(session.requests.every(r => r.request.node === 'Node-C'));
});

test('media: challenge pages never claim service access', () => {
  const session = run('media', call => {
    if (new URL(call.request.url).hostname === 'www.youtube.com') {
      return {status:200,body:'verify you are human'};
    }
    return mediaResponse(call);
  });
  assert.match(output(session), /⚠️ YouTube Premium　失败/);
});

test('media: a hanging request reaches the watchdog exactly once', () => {
  const session = run('media', call => {
    if (new URL(call.request.url).hostname === 'www.netflix.com') return {hold:true};
    return mediaResponse(call);
  });
  assert.equal(session.completed.length, 0);
  const watchdog = session.timers.find(t => t.delay >= 30000 && t.delay < 80000);
  assert.ok(watchdog);
  watchdog.fn();
  assert.equal(session.completed.length, 1);
  assert.match(output(session), /⚠️ Netflix　未完成/);
  session.requests.find(r => new URL(r.request.url).hostname === 'www.netflix.com')
    .callback(null, {status:200}, 'Netflix /title/81280792');
  watchdog.fn();
  assert.equal(session.completed.length, 1);
});
