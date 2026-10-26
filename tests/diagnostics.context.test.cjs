'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const published=require('./helpers/diagnostics.cjs');
const ROOT=path.resolve(__dirname,'..');
const files=['node-intelligence.js','network-diagnostics.js','media-unlock.js'];

test('published plugin exposes three manual tools with stable product descriptions',()=>{
  const plugin=published.plugin.source;
  assert.equal((plugin.match(/^generic then script\(/gm)||[]).length,3);
  assert.doesNotMatch(plugin,/^network-changed then script\(/m);
  assert.match(plugin,/^#!desc = 节点出口 · 网络检测 · 服务解锁检测$/m);
  assert.doesNotMatch(plugin,/auto_check|高延迟重试版/);
});

function requested(file,params,args={},config){
  const requests=[],completed=[];
  const http={get(q){requests.push(q);},post(q){requests.push(q);}};
  vm.runInNewContext(published.source(file),{
    $environment:{params},$argument:args,$config:config,$httpClient:http,
    $done(value){completed.push(value);},setTimeout(){}
  });
  return {requests,completed,nodes:requests.filter(q=>q.node!=='DIRECT').map(q=>q.node)};
}

for(const file of files){
  test(`${file}: node metadata wins consistently over stale node and fallback`,()=>{
    const result=requested(file,{node:'Old-Node',nodeInfo:{name:'Selected-Node'}},{target_policy:'Other-Node'});
    assert.ok(result.nodes.length>0);
    assert.ok(result.nodes.every(n=>n==='Selected-Node'));
  });
  test(`${file}: nested groups resolve to one concrete node`,()=>{
    const config={getConfig(){return JSON.stringify({all_policy_groups:['Proxy','Auto'],policy_select:{Proxy:'Auto',Auto:'Node-C'}});}};
    assert.ok(requested(file,{}, {target_policy:'Proxy'},config).nodes.every(n=>n==='Node-C'));
    assert.ok(requested(file,{}, {target_policy:'Proxy'},config).nodes.length>0);
  });
  test(`${file}: missing nodes, rejected policies and cycles make zero requests`,()=>{
    for(const target of ['', 'DIRECT','REJECT','REJECT-IMG','REJECT-DICT','Proxy','a\nnode','a'.repeat(201)]){
      assert.equal(requested(file,{}, {target_policy:target}).requests.length,0,target);
    }
    const config={getConfig(){return JSON.stringify({all_policy_groups:['A','B'],policy_select:{A:'B',B:'A'}});}};
    assert.equal(requested(file,{}, {target_policy:'A'},config).requests.length,0);
  });
}

test('shared transport retries the same node and suppresses duplicate callbacks',()=>{
  const requests=[],timers=[],results=[];
  const sandbox={$httpClient:{get(q,cb){requests.push(q);if(requests.length===1){cb('timeout');cb(null,{status:200},'late');}else{cb(null,{status:200},'ok');cb(null,{status:200},'duplicate');}}},
    setTimeout(fn){timers.push(fn);}};
  vm.runInNewContext(fs.readFileSync(path.join(ROOT,'src/diagnostics/common.js'),'utf8'),sandbox);
  sandbox.LoonKit.request('get',{url:'https://example.com',node:'Selected'},(...value)=>results.push(value),{attempts:2,delay:300});
  assert.equal(results.length,0);
  assert.equal(timers.length,1);
  timers[0]();
  assert.equal(requests.length,2);
  assert.ok(requests.every(q=>q.node==='Selected'));
  assert.equal(results.length,1);
  assert.equal(results[0][2],'ok');
});
