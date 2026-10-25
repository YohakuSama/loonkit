'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const ROOT=path.resolve(__dirname,'..','scripts','v20261026r1');
function launch(file,handler,options={}){
 const requests=[],timers=[],completed=[];
 const ctx={
  $argument:options.args||{target_policy:'Node-Slow'},
  $environment:{params:options.params||{node:'Node-Slow'}},
  $config:undefined,
  $httpClient:{
   get(q,cb){requests.push({q,cb});const r=handler(q,requests.length);if(r&&!r.hold)cb(r.error||null,{status:r.status??200,headers:r.headers||{}},r.body??'');},
   post(q,cb){requests.push({q,cb});const r=handler(q,requests.length);if(r&&!r.hold)cb(r.error||null,{status:r.status??200,headers:r.headers||{}},r.body??'');}
  },
  $dns:{query(q,cb){cb(null,{protocol:'doh',answers:[{type:'A',value:'203.0.113.20'}]});}},
  $done(v){completed.push(v);},
  setTimeout(fn,ms){timers.push({fn,ms});}
 };
 vm.runInNewContext(fs.readFileSync(path.join(ROOT,file),'utf8'),ctx,{timeout:4000});
 return {requests,timers,completed};
}
const content=s=>String(s.completed[0]?.content||'');
const ip=JSON.stringify({ip:'198.51.100.12',country_name:'Test Land'});
test('node: cold-start transport retry stays on selected node and succeeds',()=>{
 const s=launch('node-intelligence.js',(_q,i)=>i===1?{error:'timeout'}:{body:ip});
 assert.equal(s.requests.length,1);
 const t=s.timers.find(x=>x.ms===350);assert.ok(t);t.fn();
 assert.equal(s.requests.length,2);
 assert.ok(s.requests.every(x=>x.q.node==='Node-Slow'&&x.q.timeout>=14000));
 assert.match(content(s),/出口 IP：198.51.100.12/);
 assert.equal(s.completed.length,1);
});
test('node: repeated failure is not a false success or fallback to DIRECT',()=>{
 const s=launch('node-intelligence.js',()=>({error:'timeout'}));
 s.timers.find(x=>x.ms===350).fn();
 assert.equal(s.requests.length,2);
 assert.match(content(s),/查询失败/);
 assert.doesNotMatch(content(s),/出口 IP：198.51.100.12/);
});
test('network: transient node timeout retries while direct probe stays separate',()=>{
 let count=0;
 const s=launch('network-diagnostics.js',q=>{
  if(q.node==='DIRECT')return {status:204};
  count++;
  return count===1?{error:'timeout'}:{status:204};
 });
 assert.equal(s.requests.length,2);
 s.timers.find(x=>x.ms===300).fn();
 assert.equal(s.requests.length,3);
 assert.ok(s.requests.filter(x=>x.q.node==='Node-Slow').every(x=>x.q.timeout>=12000));
 assert.match(content(s),/节点连接正常/);
 assert.equal(s.completed.length,1);
});
test('network: watchdog cannot create a success from hanging requests',()=>{
 const s=launch('network-diagnostics.js',()=>({hold:true}));
 assert.equal(s.completed.length,0);
 s.timers.find(x=>x.ms===57000).fn();
 assert.equal(s.completed.length,1);
 assert.match(content(s),/检测超时/);
});
function reply(q) {
 const u=new URL(q.url),host=u.hostname;
 if(host==='startup.core.indazn.com')return {body:JSON.stringify({GeolocatedCountry:'JP'})};
 if(host==='us1-prod-direct.discoveryplus.com')return {body:JSON.stringify({data:{attributes:{token:'placeholder'}}})};
 if(host==='www.paramountplus.com')return {body:'OK'};
 if(host==='disney.api.edge.bamgrid.com')return {body:JSON.stringify({extensions:{sdk:{session:{inSupportedLocation:true,location:{countryCode:'JP'}}}}})};
 if(host==='www.netflix.com')return {body:'Netflix /title/81280792'};
 if(host==='www.youtube.com')return {body:'{"GL":"JP"}'};
 if(u.pathname==='/cdn-cgi/trace')return {body:'loc=JP\n'};
 if(host==='chatgpt.com')return {body:'ChatGPT OpenAI'};
 return {status:503};
}
test('unlock: first cold-start timeout is retried on same node; no false block',()=>{
 let errCount=0;
 const s=launch('media-unlock.js',q=>{
  if(new URL(q.url).hostname==='www.youtube.com' && errCount++===0)return {error:'timeout'};
  return reply(q);
 });
 assert.ok(s.requests.some(x=>new URL(x.q.url).hostname==='www.youtube.com'&&x.q.timeout>=11000));
 assert.ok(s.requests.every(x=>x.q.node==='Node-Slow'));
 assert.match(content(s),/YouTube Premium/);
 assert.match(content(s),/可访问：7 \/ 7/);
 assert.equal(s.completed.length,1);
});
test('unlock: service remains unknown after persistent error; watchdog is guarded',()=>{
 const s=launch('media-unlock.js',q=>new URL(q.url).hostname==='www.netflix.com'?{error:'timeout'}:reply(q));
 assert.match(content(s),/Netflix　失败/);
 assert.doesNotMatch(content(s),/可访问：7 \/ 7/);
 assert.ok(s.requests.filter(x=>new URL(x.q.url).hostname==='www.netflix.com').length===2);
 s.timers.find(x=>x.ms===69000).fn();assert.equal(s.completed.length,1);
});
