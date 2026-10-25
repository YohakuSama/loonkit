/* LoonKit · 节点出口信息 */
(function () {
  "use strict";
  var args=typeof $argument==="object"&&$argument||{};
  var env=typeof $environment==="object"&&$environment&&$environment.params||{};
  var info=env.nodeInfo&&typeof env.nodeInfo==="object"?env.nodeInfo:{};
  var providers=[
    {name:"ipquery.io",url:"https://api.ipquery.io/?format=json"},
    {name:"ipwho.is",url:"https://ipwho.is/"}
  ];
  var closed=false;

  function value(v){return typeof v==="string"?v.trim():"";}
  function clean(v){
    return typeof v==="string"||typeof v==="number"?
      String(v).replace(/[\u0000-\u001f\u007f]/g," ").trim().slice(0,80):"";
  }
  function short(v,max){
    var x=Array.from(clean(v));
    return x.length<=max?x.join(""):x.slice(0,max-9).join("")+"…"+x.slice(-8).join("");
  }
  function selectNode(){
    var name=value(info.name)||value(info.tag)||value(env.node)||
      value(env.policyGroup)||value(args.target_policy);
    if(!name||name.length>200||/[\u0000-\u001f\u007f]/.test(name))return "";
    var cfg=typeof $config==="object"&&$config,groups=[],select={};
    try {
      if(cfg&&typeof cfg.getConfig==="function"){
        var conf=JSON.parse(cfg.getConfig()||"{}");
        if(Array.isArray(conf.all_policy_groups))groups=conf.all_policy_groups;
        if(conf.policy_select&&typeof conf.policy_select==="object")
          select=conf.policy_select;
      }
    }catch(e){}
    var visited={},depth=0;
    while(depth++<8){
      if(visited[name])return "";
      visited[name]=true;
      if(/^(DIRECT|REJECT|REJECT-DROP)$/i.test(name))return "";
      var group=groups.some(function(x){
        return x===name||x&&typeof x==="object"&&(x.name===name||x.tag===name);
      });
      var child="";
      try{
        if(cfg&&typeof cfg.getSelectedPolicy==="function")
          child=value(cfg.getSelectedPolicy(name));
      }catch(e){}
      if(!child)child=value(select[name]);
      if(child&&child!==name){name=child;continue;}
      if(group||/^(Proxy|Auto|Fallback|ALL_Filter)$/i.test(name))return "";
      return name;
    }
    return "";
  }
  var node=selectNode();
  function validIP(ip){
    if(typeof ip!=="string"||ip.length<2||ip.length>45)return false;
    if(/^\d{1,3}(\.\d{1,3}){3}$/.test(ip))
      return ip.split(".").every(function(part){return Number(part)<=255;});
    if(!/^[0-9a-f:]+$/i.test(ip)||ip.indexOf(":")<0)return false;
    var sections=ip.split("::");
    if(sections.length>2)return false;
    var fields=ip.split(":").filter(function(x){return x.length>0;});
    if(fields.some(function(x){return !/^[0-9a-f]{1,4}$/i.test(x)}))return false;
    return sections.length===2?fields.length<8:fields.length===8;
  }
  function country(code){
    code=clean(code).toUpperCase();
    return /^[A-Z]{2}$/.test(code)?code:"";
  }
  function asn(n){
    var x=clean(n).replace(/^AS/i,"");
    return /^\d{1,10}$/.test(x)?"AS"+String(Number(x)):"";
  }
  function normalize(x,source){
    if(!x||typeof x!=="object"||x.success===false||!validIP(x.ip))return null;
    var loc=source===0?x.location||{}:x;
    var net=source===0?x.isp||{}:x.connection||{};
    return {
      ip:x.ip,country:country(loc.country_code),region:clean(source===0?loc.state:loc.region),
      city:clean(loc.city),asn:asn(net.asn),isp:clean(net.isp),
      provider:providers[source].name
    };
  }
  function lookup(policy,index,done){
    var once=false;
    function finish(item){if(once)return;once=true;done(item);}
    try{
      $httpClient.get({
        url:providers[index].url,node:policy,timeout:8500,
        headers:{"Accept":"application/json"},
        "auto-cookie":false,"auto-redirect":false
      },function(err,response,body){
        if(err||Number(response&&response.status)!==200||
           typeof body!=="string"||body.length>100000)return finish(null);
        try{finish(normalize(JSON.parse(body),index));}
        catch(e){finish(null);}
      });
    }catch(e){finish(null);}
  }
  function compare(a,b,field){
    var left=a&&a[field]||"",right=b&&b[field]||"";
    if(left&&right)return left.toLowerCase()===right.toLowerCase()?left:"不一致";
    return left||right||"未知";
  }
  function inspect(policy,done){
    var values=[null,null],waiting=2;
    providers.forEach(function(_,i){
      lookup(policy,i,function(item){
        values[i]=item;
        if(!--waiting)done(values);
      });
    });
  }
  function exit(values){
    var a=values[0],b=values[1];
    if(!a&&!b)return {ip:"",lines:["出口 IP：查询失败"]};
    if(a&&b&&a.ip.toLowerCase()!==b.ip.toLowerCase()){
      return {ip:"",lines:[
        "出口 IP：结果不一致",
        "ipquery.io："+a.ip,
        "ipwho.is："+b.ip,
        "地区 / ASN：待核实"
      ]};
    }
    var ip=(a||b).ip;
    var source=a&&b?"双源一致":(a||b).provider+"（单源）";
    var lines=[
      "出口 IP："+ip,
      "核验："+source,
      "地区："+compare(a,b,"country"),
      "ASN："+compare(a,b,"asn"),
      "运营商："+short(compare(a,b,"isp"),32)
    ];
    if(a&&b){
      var city=compare(a,b,"city");
      if(city!=="未知"&&city!=="不一致")lines.push("城市："+short(city,32));
    }
    return {ip:ip,lines:lines};
  }
  function finish(content){
    if(closed)return;
    closed=true;
    $done({title:"节点信息",content:content});
  }
  if(!node){
    finish("请从单个节点运行，或在检测节点中指定具体节点。");
    return;
  }
  var result=[],pending=args.compare_direct===true?2:1;
  function join(){
    if(--pending)return;
    var out=exit(result[0]);
    var lines=["节点："+short(node,33),"",].concat(out.lines);
    if(args.compare_direct===true){
      var direct=exit(result[1]);
      lines.push("","直连出口："+(direct.ip||"待核实"));
      if(out.ip&&direct.ip)
        lines.push("出口对照："+(out.ip.toLowerCase()===direct.ip.toLowerCase()?"相同":"不同"));
    }
    finish(lines.join("\n"));
  }
  inspect(node,function(data){result[0]=data;join();});
  if(args.compare_direct===true)
    inspect("DIRECT",function(data){result[1]=data;join();});
  setTimeout(function(){finish("节点："+short(node,33)+"\n出口 IP：查询超时");},28000);
})();
