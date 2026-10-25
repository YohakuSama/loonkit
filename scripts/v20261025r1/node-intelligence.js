/* LoonKit · Node Egress v2.7 — compact manual report.
 * Observed exit IP is not necessarily the proxy server's entry IP.
 * All provider classifications are unverified hints, not quality scores. */
(function () {
  "use strict";
  var args=(typeof $argument==="object" && $argument)||{};
  var ctx=(typeof $environment==="object" && $environment && $environment.params)||{};
  var PRIMARY="https://api.ipquery.io/?format=json";
  var BACKUP="https://ipwho.is/";
  var finished=false;
  function choose(v){return typeof v==="string" && v.trim()?v.trim():"";}
  var info=ctx.nodeInfo && typeof ctx.nodeInfo==="object"?ctx.nodeInfo:{};
  var route=choose(ctx.node)||choose(info.name)||choose(info.tag)||
    choose(ctx.policyGroup)||choose(args.target_policy)||"Proxy";
  function safe(x){
    if(typeof x==="number"&&isFinite(x)) x=String(x);
    return typeof x==="string"&&x.trim()?
      x.replace(/[\u0000-\u001f\u007f]/g," ").trim().slice(0,80):"未知";
  }
  function ipv4(s) {
    if(!/^\d{1,3}(?:\.\d{1,3}){3}$/.test(s)) return false;
    return s.split(".").every(function(x){return Number(x)<=255;});
  }
  function validIP(s){
    if(typeof s!=="string"||s.length<2||s.length>45) return false;
    if(s.indexOf(":")<0) return ipv4(s);
    if(!/^[0-9a-f:.]+$/i.test(s)||s.indexOf(":::")>=0) return false;
    var split=s.split("::");
    if(split.length>2) return false;
    var pieces=[];
    split.forEach(function(v){if(v) pieces=pieces.concat(v.split(":"));});
    if(pieces.some(function(v){return !/^[0-9a-f]{1,4}$/i.test(v);})) return false;
    return split.length===2?pieces.length<8:pieces.length===8;
  }
  function boundedNumber(x,min,max) {
    return typeof x==="number" && isFinite(x) && x>=min && x<=max ? x : null;
  }
  function optionalText(x) {
    var v=safe(x);
    return v==="未知"?"":v;
  }
  function truth(x) {
    return typeof x==="boolean"?x:null;
  }
  function asn(x) {
    if (x===null || x===undefined || x==="") return "未知";
    var t=safe(String(x)).replace(/^AS/i,"");
    return /^\d+$/.test(t)?"AS"+t:safe(x);
  }
  function toNode(x) {
    if(!x || typeof x!=="object"||x.success===false||!validIP(x.ip)) return null;
    if(x.location && typeof x.location==="object" && x.isp && typeof x.isp==="object") {
      var l=x.location,r=x.risk&&typeof x.risk==="object"?x.risk:{};
      return {
        ip:x.ip,country:safe(l.country),countryCode:safe(l.country_code),
        region:safe(l.state),city:safe(l.city),timezone:optionalText(l.timezone),
        zip:optionalText(l.zipcode),lat:boundedNumber(l.latitude,-90,90),
        lon:boundedNumber(l.longitude,-180,180),
        asn:asn(x.isp.asn),isp:safe(x.isp.isp),org:safe(x.isp.org),
        datacenter:truth(r.is_datacenter),mobile:truth(r.is_mobile),
        vpn:truth(r.is_vpn),proxy:truth(r.is_proxy),tor:truth(r.is_tor),
        riskScore:boundedNumber(r.risk_score,0,100),provider:"ipquery.io"
      };
    }
    if(x.connection || (x.country && x.ip)) {
      var c=x.connection&&typeof x.connection==="object"?x.connection:{};
      var timezone=typeof x.timezone==="object"&&x.timezone?x.timezone.id:x.timezone;
      return {
        ip:x.ip,country:safe(x.country),countryCode:safe(x.country_code),
        region:safe(x.region),city:safe(x.city),timezone:optionalText(timezone),
        zip:optionalText(x.postal),lat:boundedNumber(x.latitude,-90,90),
        lon:boundedNumber(x.longitude,-180,180),
        asn:asn(c.asn),isp:safe(c.isp),org:safe(c.org),
        datacenter:null,mobile:null,vpn:null,proxy:null,tor:null,
        riskScore:null,provider:"ipwho.is"
      };
    }
    return null;
  }

  function explain(err){
    var str=String(err||"").toLowerCase();
    if(/timeout|timed out/.test(str))return "连接超时";
    if(/dns|resolv|host/.test(str))return "域名解析失败";
    if(/tls|ssl|certificat/.test(str))return "TLS/证书失败";
    return "请求失败";
  }
  function request(url,node,cb){
    var done=false;
    function finish(err,val){
      if(done)return;
      done=true;
      cb(err,val);
    }
    try {
      $httpClient.get({url:url,node:node,timeout:8500,
        headers:{"Accept":"application/json"},"auto-cookie":false,"auto-redirect":false},
      function(err,response,body){
        if(err) return finish(explain(err),null);
        if(Number(response && response.status)!==200)
          return finish("HTTP "+String(response&&response.status||"未知"),null);
        if(typeof body!=="string"||body.length>100000)
          return finish("响应体格式不正确",null);
        try {
          var normalized=toNode(JSON.parse(body));
          if(!normalized)return finish("IP 数据格式不兼容",null);
          finish(null,normalized);
        } catch(e) {finish("JSON 解析失败",null);}
      });
    }catch(e){finish(explain(e),null);}
  }
  function lookup(node,done){
    request(PRIMARY,node,function(err,item){
      if(item)return done(null,item);
      request(BACKUP,node,function(err2,backup){
        done(backup?null:"主服务："+err+"；备用："+err2,backup);
      });
    });
  }
  function category(item){
    if(item.mobile===true)return "移动网络";
    if(item.datacenter===true)return "机房 / 云服务";
    if(item.datacenter===false && item.mobile===false)return "其他 / 未确认";
    return "未知";
  }
  function flag(value) {
    return value===true?"是":value===false?"否":"未知";
  }
  function localInfo(ip) {
    if(typeof $utils==="undefined" || !$utils)return null;
    function call(method) {
      try {
        return typeof $utils[method]==="function" ? safe($utils[method](ip)) : "无数据";
      } catch(e){return "无数据";}
    }
    return {geo:call("geoip"),asn:call("ipasn"),org:call("ipaso")};
  }
  function configuredEntrance() {
    // This is the proxy server configured in Loon, not a verified relay-chain first hop.
    var input=choose(info.address);
    if(!input||input.length>253||/[\/?#@\s\x00-\x1f]/.test(input))return "";
    var host=input;
    var bracket=input.match(/^\[([0-9a-f:]+)\](?::[0-9]{1,5})?$/i);
    if(bracket) {
      if(!validIP(bracket[1]))return "";
      host=bracket[1];
    } else {
      var parts=input.match(/^([^:]+)(?::([0-9]{1,5}))?$/);
      if(!parts)return "";
      host=parts[1];
      if(!ipv4(host)&&!/^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$/i.test(host))return "";
      if(host.indexOf("..")>=0||host.startsWith("-")||host.endsWith("-"))return "";
    }
    return host;
  }
  // Keep native iPhone dialogs compact; preserve semantics and source uncertainty.
  function show(item,direct) {
    function brief(value,max) {
      var chars=Array.from(safe(value));
      return chars.length<=max?chars.join(""):
        chars.slice(0,max-8).join("")+"…"+chars.slice(-7).join("");
    }
    var loc=[item.countryCode!=="未知"?item.countryCode:item.country,
      item.region,item.city].filter(function(x){return x&&x!=="未知";});
    if(loc.length>=3&&loc[1]===loc[2])loc.splice(1,1);
    var lines=[
      "节点："+brief(route,26),"",
      "出口信息",
      "IP："+item.ip,
      "地区："+brief(loc.join(" · ")||"未知",38),
      "运营商："+brief(item.isp,34),
      "ASN："+item.asn,
      "类型："+category(item)
    ];
    var entry=configuredEntrance();
    if(entry&&entry!==item.ip)lines.push("入口："+brief(entry,34));
    if(item.timezone)lines.push("时区："+brief(item.timezone,34));
    var flags=[item.datacenter,item.mobile,item.vpn,item.proxy,item.tor];
    if(flags.some(function(x){return x!==null;})){
      lines.push("","网络特征",
        "机房："+flag(item.datacenter)+"  移动："+flag(item.mobile),
        "VPN："+flag(item.vpn)+"  代理："+flag(item.proxy)+"  Tor："+flag(item.tor));
    }
    if(item.riskScore!==null)lines.push("风险评分："+item.riskScore+"/100");
    var local=localInfo(item.ip);
    if(local && local.geo!=="无数据" && local.geo!=="未知" &&
        item.countryCode!=="未知" && local.geo.toUpperCase()!==item.countryCode.toUpperCase())
      lines.push("本地 GeoIP："+brief(local.geo,28));
    if(direct)lines.push("","直连出口："+direct.ip,
      "出口对照："+(item.ip===direct.ip?"相同":"不同"));
    else if(args.compare_direct===true&&route!=="DIRECT")
      lines.push("","直连出口：查询失败");
    lines.push("","数据来源："+item.provider);
    return lines.join("\n");
  }

  function done(msg){
    if(finished)return;
    finished=true;
    $done({title:"节点信息",content:msg});
  }
  if(route.length>200 || /[\r\n\u0000-\u001f]/.test(route)) {
    done("节点或策略名称无效。");return;
  }
  if(args.compare_direct!==true||route==="DIRECT"){
    lookup(route,function(err,item){
      if(err)return done("节点/策略："+safe(route)+"\n查询失败："+safe(err)+
        "\n请检查当前节点是否可用。");
      done(show(item,null));
    });
  }else{
    // Optional direct/exit comparison runs both lookups in parallel.
    var waiting=2,proxyResult=null,proxyError="",directResult=null;
    function joined(){
      if(--waiting)return;
      if(proxyError)return done("节点/策略："+safe(route)+"\n查询失败："+safe(proxyError)+
        "\n请检查当前节点是否可用。");
      done(show(proxyResult,directResult));
    }
    lookup(route,function(err,item){
      proxyError=err||"";proxyResult=item;joined();
    });
    lookup("DIRECT",function(err,item){
      directResult=err?null:item;joined();
    });
  }
})();
