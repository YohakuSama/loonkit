/* LoonKit · manual node/network/DNS diagnostics.
 * Inspect the resolver used by the native Loon DNS stack. This cannot prove
 * that browsers or other apps do not use independent encrypted DNS.
 * No routing, DNS, policy, or VPN settings are modified. */
(function () {
  "use strict";
  var DIRECT_URL = "http://wifi.vivo.com.cn/generate_204";
  var MANUAL_URL = "https://www.gstatic.com/generate_204";
  var finished = false;

  setTimeout(function () {
    finish("检测超时，请稍后重试或查看 Loon 连接记录。");
  }, 57000);

  function finish(message) {
    if (finished) return;
    finished = true;
    // Loon does not guarantee a clearTimeout API. Guard against late callbacks.
    $done(message && typeof message==="object"?message:{title:"网络检测",content:message});
  }
  function errorText(error) {
    var msg = String(error && (error.message || error) || "").toLowerCase();
    if (/timeout|timed out/.test(msg)) return "超时";
    if (/certificat|tls|ssl/.test(msg)) return "TLS 错误";
    if (/dns|resolv|host/.test(msg)) return "域名解析失败";
    return "连接失败";
  }
  function httpProbe(label, url, policy, cb) {
    var start=Date.now(), attempts=0, settled=false;
    function done(ok, detail) {
      if(settled)return;
      settled=true;
      cb({label:label,ok:ok,detail:detail,ms:Date.now()-start});
    }
    function probe(){
      if(settled)return;
      attempts++;
      var called=false;
      function finish(ok, detail, transient) {
        if(called||settled)return;
        called=true;
        if(transient&&attempts<2){
          setTimeout(probe,300);
        } else done(ok,detail);
      }
      try {
        $httpClient.get({url:url,node:policy,timeout:12500,insecure:false,
          "auto-redirect":false,"auto-cookie":false},function(error,response){
          if(error)return finish(false,errorText(error),true);
          var status=Number(response&&response.status);
          if(status===204)return finish(true,"HTTP 204 · 正常",false);
          if(status===200)return finish(null,"响应异常（HTTP 200），可能需要网络认证",false);
          if(status>=300&&status<400)return finish(null,"HTTP "+status+" · 目标重定向",false);
          if(status>=500&&status<=599)return finish(null,"HTTP "+status+" · 目标服务暂时异常",true);
          if(status>=400&&status<500)return finish(null,"HTTP "+status+" · 服务返回错误",false);
          finish(null,"HTTP "+(status||"未知")+"（无法确认）",false);
        });
      }catch(error){finish(false,errorText(error),true);}
    }
    probe();
  }
  function nativeDns(cb) {
    var label="DNS 解析";
    if (typeof $dns === "undefined" || !$dns || typeof $dns.query !== "function") {
      cb({label:label,ok:null,detail:"当前 Loon 版本不支持 DNS 检测"});
      return;
    }
    var called=false;
    try {
      $dns.query({domain:"example.com",protocol:"auto",timeout:10500},function(error,reply){
        if (called) return;
        called=true;
        if (error || !reply) {
          cb({label:label,ok:false,detail:"查询失败："+errorText(error)});
          return;
        }
        var answers=Array.isArray(reply.answers)?reply.answers:[];
        if (!answers.some(function(item){return item && (item.type==="A" || item.type==="AAAA") && item.value;})) {
          cb({label:label,ok:false,detail:"没有获得有效的解析地址"});
          return;
        }

        var protocol=String(reply.protocol || "unknown").toLowerCase().trim();
        var server=String(reply.server || "").trim().slice(0,180);
        // A successful answer proves resolution, not capture of all DNS traffic.
        if (reply.fromCache===true) {
          cb({label:label,ok:true,detail:"解析成功（缓存）"});
          return;
        }

        // DNS is user-configurable. Identify the protocol without requiring a
        // specific public resolver. A bare "https://" is not a full URL.
        var httpsUrl=/^https:\/\/[^\s\/?#]+(?:[\/?#]|$)/i.test(server);
        var tlsUrl=/^(?:tls|dot):\/\/[^\s\/?#]+/i.test(server);
        if (protocol==="udp" || protocol==="system") {
          cb({label:label,ok:true,detail:"解析成功 · 普通 DNS"});
        } else if (protocol==="doh" || (protocol==="auto" && httpsUrl)) {
          cb({label:label,ok:true,detail:"解析成功 · DoH"});
        } else if (protocol==="dot" || (protocol==="auto" && tlsUrl)) {
          cb({label:label,ok:true,detail:"解析成功 · DoT"});
        } else if (protocol==="doh3" || protocol==="quic") {
          cb({label:label,ok:true,detail:"解析成功 · Loon 报告加密 DNS"});
        } else {
          cb({label:label,ok:true,detail:"解析成功",
            notice:"已解析，但无法确认所用 DNS 传输方式。"});
        }
      });
    } catch (error) {
      if (!called) cb({label:label,ok:false,detail:"DNS API 调用异常"});
    }
  }
  function resultLine(value) {
    return (value.ok===null?"—":value.ok?"✓":"✗")+" "+value.label+"："+value.detail+
      (typeof value.ms==="number"?"（"+value.ms+" ms）":"");
  }
  function choose(value) {
    return typeof value==="string" && value.trim()?value.trim():"";
  }
  function safe(value) {
    return String(value||"").replace(/[\u0000-\u001f\u007f]/g," ").trim().slice(0,100);
  }
  function resolveNode() {
    var env=(typeof $environment==="object" && $environment && $environment.params)||{};
    var args=(typeof $argument==="object" && $argument)||{};
    var info=env.nodeInfo && typeof env.nodeInfo==="object"?env.nodeInfo:{};
    // A node-menu invocation wins over the plugin's fallback policy argument.
    var selected=choose(env.node)||choose(info.name)||choose(info.tag);
    if(!selected)selected=choose(env.policyGroup)||choose(args.target_policy);
    if(!selected)return "";
    var config=typeof $config==="object"&&$config,groups=[],selection={};
    try {
      if(config&&typeof config.getConfig==="function"){
        var snapshot=JSON.parse(config.getConfig()||"{}");
        if(Array.isArray(snapshot.all_policy_groups))groups=snapshot.all_policy_groups;
        if(snapshot.policy_select&&typeof snapshot.policy_select==="object")
          selection=snapshot.policy_select;
      }
    }catch(e){}
    var visited={},depth=0;
    while(depth++<8){
      if(visited[selected])return "";
      visited[selected]=true;
      if(/^(DIRECT|REJECT|REJECT-DROP)$/i.test(selected))return "";
      var isGroup=groups.some(function(group){
        return group===selected || group&&typeof group==="object"&&
          (group.name===selected||group.tag===selected);
      });
      var child="";
      try {
        if(config&&typeof config.getSelectedPolicy==="function")
          child=choose(config.getSelectedPolicy(selected));
      }catch(e){}
      if(!child)child=choose(selection[selected]);
      if(child&&child!==selected){selected=child;continue;}
      if(isGroup||/^(Proxy|Auto|Fallback|ALL_Filter)$/i.test(selected))return "";
      return selected;
    }
    return "";
  }
  // Native alert content is proportional-font text, not an HTML table.
  function shortNode(value) {
    var chars=Array.from(safe(value));
    return chars.length<=24?chars.join(""):chars.slice(0,13).join("")+"…"+chars.slice(-7).join("");
  }
  function display(node,direct,proxy,dns) {
    function state(item){
      return (item.ok===true?"正常":item.ok===false?"失败":"待确认")+
        (typeof item.ms==="number"?" · "+item.ms+" ms":"");
    }
    var headline=proxy.ok===true?"节点连接正常":
      proxy.ok===false?"本次节点探测未通过":"节点状态待确认";
    var lines=[
      "节点："+shortNode(node),"",
      "连接状态",
      "节点："+state(proxy),
      "直连："+state(direct),
      "DNS："+(dns.ok===true?"正常":dns.ok===false?"失败":"待确认")
    ];
    if(proxy.ok!==true)lines.push("节点详情："+proxy.detail+"（不等于节点始终不可用）");
    if(direct.ok!==true)lines.push("直连详情："+direct.detail);
    lines.push("DNS 详情："+dns.detail);
    if(dns.notice)lines.push("DNS："+dns.notice);
    lines.push("","结论："+headline);
    return {title:"网络检测",content:lines.join("\n")};
  }

  function manual() {
    var target=resolveNode();
    if(!target || /[\u0000-\u001f\u007f]/.test(target)) {
      finish({title:"网络检测",
        content:"请在单个节点的菜单中运行网络检测，或在插件的「检测策略」中填写具体节点名称。"});
      return;
    }
    var pending=2, results={};
    function collect(key,item){
      if(results[key])return;
      results[key]=item;
      if(--pending!==0)return;
      nativeDns(function(dns){finish(display(target,results.direct,results.node,dns));});
    }
    httpProbe("直连网络",DIRECT_URL,"DIRECT",function(x){collect("direct",x);});
    httpProbe("节点连接",MANUAL_URL,target,function(x){collect("node",x);});
  }
  manual();
})();
