/*
 * LoonKit · 节点解锁查询
 * 各平台检测方法参考 KOP-XIAO QuantumultX streaming-ui-check.js。
 * 检测脚本由 LoonKit 自身托管和执行，不加载第三方仓库的脚本。
 * 上游参考：https://github.com/KOP-XIAO/QuantumultX
 */
(function () {
  "use strict";
  var args=typeof $argument==="object"&&$argument||{};
  var env=typeof $environment==="object"&&$environment.params||{};
  var info=env.nodeInfo&&typeof env.nodeInfo==="object"?env.nodeInfo:{};
  function string(v){return typeof v==="string"?v.trim():"";}
  function resolveNode(){
    var selected=string(info.name)||string(info.tag)||string(env.node)||
      string(env.policyGroup)||string(args.target_policy);
    if(!selected||selected.length>200||/[\u0000-\u001f\u007f]/.test(selected))return "";
    var config=typeof $config==="object"&&$config,groups=[],selection={};
    try{
      if(config&&typeof config.getConfig==="function"){
        var snapshot=JSON.parse(config.getConfig()||"{}");
        if(Array.isArray(snapshot.all_policy_groups))groups=snapshot.all_policy_groups;
        if(snapshot.policy_select&&typeof snapshot.policy_select==="object")
          selection=snapshot.policy_select;
      }
    }catch(e){}
    var seen={},depth=0;
    while(depth++<8){
      if(seen[selected])return "";
      seen[selected]=true;
      if(/^(DIRECT|REJECT|REJECT-DROP)$/i.test(selected))return "";
      var isGroup=groups.some(function(group){
        return group===selected||group&&typeof group==="object"&&
          (group.name===selected||group.tag===selected);
      });
      var child="";
      try{
        if(config&&typeof config.getSelectedPolicy==="function")
          child=string(config.getSelectedPolicy(selected));
      }catch(e){}
      if(!child)child=string(selection[selected]);
      if(child&&child!==selected){selected=child;continue;}
      if(isGroup||/^(Proxy|Auto|Fallback|ALL_Filter)$/i.test(selected))return "";
      return selected;
    }
    return "";
  }
  var node=resolveNode();
  if(!node){
    $done({title:"解锁检测",content:"请从单个节点运行，或在检测策略中指定具体节点。"});return;
  }
  var items=[
    ["dazn","DAZN"],["discovery","Discovery+"],["paramount","Paramount+"],
    ["disney","Disney+"],["netflix","Netflix"],["chatgpt","ChatGPT"],
    ["youtube","YouTube Premium"]
  ];
  var result={},closed=false,completeCount=0,active=0,queue=[],MAX_HTTP=7;
  function status(r){return Number(r&&r.status)||0;}
  function header(r,key){
    var h=r&&r.headers||{},keys=Object.keys(h);
    for(var i=0;i<keys.length;i++)if(keys[i].toLowerCase()===key.toLowerCase())return String(h[keys[i]]||"");
    return "";
  }
  function parse(s){try{return JSON.parse(s);}catch(e){return null;}}
  function region(s){var code=String(s||"").trim().toUpperCase();return /^[A-Z]{2}$/.test(code)?code:"";}
  function find(s,regex){var m=String(s||"").match(regex);return m?region(m[1]):"";}
  function verdict(state,geo){return {state:state,geo:region(geo)};}
  function enqueue(url,options,callback){
    if(closed)return;
    queue.push({url:url,options:options||{},callback:callback});
    pump();
  }
  function pump(){
    while(!closed&&active<MAX_HTTP&&queue.length){
      (function(task){
        active++;var once=false,o=task.options;
        var request={
          url:task.url,node:node,timeout:o.timeout||5000,
          insecure:false,
          headers:{"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/94.0.4606.61 Safari/537.36"}
        };
        // Preserve Loon's default redirect/cookie behavior unless a probe needs the raw response.
        if(o.redirect===false)request["auto-redirect"]=false;
        if(o.cookie===false)request["auto-cookie"]=false;
        var headers=o.headers||{};
        Object.keys(headers).forEach(function(k){request.headers[k]=headers[k];});
        if(o.method==="POST")request.body=o.body;
        function completed(err,response,body){
          if(once)return;once=true;active--;
          if(!closed)task.callback(err,response||{},typeof body==="string"?body.slice(0,200000):"");
          if(!closed)pump();
        }
        try{
          var method=o.method==="POST"?$httpClient.post:$httpClient.get;
          if(typeof method!=="function")throw new Error("No HTTP method");
          method.call($httpClient,request,completed);
        }catch(e){completed(e,null,"");}
      })(queue.shift());
    }
  }
  function get(url,callback,options){enqueue(url,options||{},callback);}
  function post(url,body,headers,callback){
    enqueue(url,{method:"POST",body:body,headers:headers},callback);
  }
  function test(id,finish){
    if(id==="dazn"){
      post("https://startup.core.indazn.com/misl/v5/Startup",
        JSON.stringify({LandingPageKey:"generic",Platform:"web",PlatformAttributes:{},Manufacturer:"",PromoCode:"",Version:"2"}),
        {"Content-Type":"application/json"},function(err,res,body){
          if(err||status(res)!==200)return finish(verdict("failed"));
          var data=parse(body),geo=region(data&&data.GeolocatedCountry)||
            find(body,/"GeolocatedCountry"\s*:\s*"([^"]+)"/);
          finish(verdict(geo?"supported":"unsupported",geo));
        });
    }else if(id==="discovery"){
      get("https://us1-prod-direct.discoveryplus.com/token?deviceId=d1a4a5d25212400d1e6985984604d740&realm=go&shortlived=true",
        function(err,res,body){
          if(err||status(res)!==200)return finish(verdict("failed"));
          var data=parse(body),attrs=data&&data.data&&data.data.attributes;
          var token=attrs&&attrs.token;
          if(typeof token!=="string"||!token||token.length>4096)return finish(verdict("failed"));
          var country=region(attrs.currentLocationTerritory||attrs.territory||attrs.countryCode);
          finish(verdict(country?"supported":"available",country));
        });
    }else if(id==="paramount"){
      get("https://www.paramountplus.com/",function(err,res,body){
        if(err)return finish(verdict("failed"));
        if(status(res)===200){
          if(/not available in your (?:region|country)|unsupported.country/i.test(body))
            return finish(verdict("unsupported"));
          return finish(verdict("supported"));
        }
        if(status(res)===302){
          var dest=header(res,"location");
          if(/unavailable|not.available|unsupported/i.test(dest))return finish(verdict("unsupported"));
          // A routine locale or canonical-domain redirect is not a regional block.
          return finish(verdict("failed"));
        }
        finish(verdict(status(res)===451?"unsupported":"failed"));
      });
    }else if(id==="disney"){
      var payload=JSON.stringify({
        query:"mutation registerDevice($input: RegisterDeviceInput!) { registerDevice(registerDevice: $input) { grant { grantType assertion } } }",
        variables:{input:{applicationRuntime:"chrome",deviceFamily:"browser",deviceLanguage:"en",deviceProfile:"windows",
          attributes:{browserName:"chrome",browserVersion:"94.0.4606",manufacturer:"microsoft",
            model:null,operatingSystem:"windows",operatingSystemVersion:"10.0",osDeviceIds:[]}}}
      });
      post("https://disney.api.edge.bamgrid.com/graph/v1/device/graphql",payload,{
        "Authorization":"ZGlzbmV5JmJyb3dzZXImMS4wLjA.Cu56AgSfBTDag5NiRA81oLHkDZfu5L3CKadnefEAY84",
        "Content-Type":"application/json","Accept-Language":"en","User-Agent":"UA"
      },function(err,res,body){
        if(err||status(res)!==200)return finish(verdict("failed"));
        var j=parse(body),session=j&&j.extensions&&j.extensions.sdk&&j.extensions.sdk.session;
        if(!session)return finish(verdict("failed"));
        var geo=region(session.location&&session.location.countryCode);
        if(typeof session.inSupportedLocation!=="boolean")return finish(verdict("failed"));
        finish(verdict(session.inSupportedLocation?"supported":"coming",geo));
      });
    }else if(id==="netflix"){
      var film="81280792";
      get("https://www.netflix.com/title/"+film,function(err,res,body){
        if(err)return finish(verdict("failed"));
        var sc=status(res);
        if(sc===403||sc===451)return finish(verdict("unsupported"));
        if(sc===404)return finish(verdict("uncertain"));
        if(sc!==200)return finish(verdict("failed"));
        var origin=header(res,"x-originating-url"),loc=header(res,"location");
        if(/\/login|\/signup|\/browse\/login|\/account\//i.test(loc))
          return finish(verdict("failed"));
        if(/sign in to netflix|enter your email to create or restart|captcha|verify you are human/i.test(body))
          return finish(verdict("failed"));
        var isTitle=/netflix\.com/i.test(origin)&&origin.indexOf("/title/"+film)>=0 ||
          /netflix/i.test(body)&&(/\/title\/81280792|81280792/i.test(body));
        if(!isTitle)return finish(verdict("failed"));
        var parts=origin.split("/"),area=parts.length>3?parts[3].split("-")[0].toUpperCase():"";
        finish(verdict("full",area==="TITLE"?"":region(area)));
      },{timeout:6000,headers:{"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"}});
    }else if(id==="youtube"){
      get("https://www.youtube.com/premium",function(err,res,body){
        if(err||status(res)!==200)return finish(verdict("failed"));
        if(body.indexOf("Premium is not available in your country")!==-1)
          return finish(verdict("unsupported"));
        var geo=find(body,/"GL":"(.*?)"/);
        if(!geo)geo=find(body,/"(?:countryCode|country_code)"\s*:\s*"([A-Za-z]{2})"/);
        if(!geo&&body.indexOf("www.google.cn")!==-1)geo="CN";
        if(/google accounts|verify you are human|unusual traffic|sign in - google/i.test(body))return finish(verdict("failed"));
        finish(verdict("supported",geo));
      },{timeout:10000});
    }else if(id==="chatgpt"){
      get("https://chatgpt.com/",function(err,res,body){
        var sc=status(res),redirect=header(res,"location");
        if(/unsupported_country|disallowed isp|not available in your country/i.test(body))
          return finish(verdict("unsupported"));
        var isChallenge=/cloudflare|captcha|verify you are human|just a moment/i.test(body);
        var accepted=sc===200&&!isChallenge&&/chatgpt|openai/i.test(body)||
          [301,302,307,308].indexOf(sc)>=0&&/^https:\/\/(?:chatgpt\.com|auth\.openai\.com|login\.openai\.com)\//i.test(redirect);
        function finishCountry(ok){
          if(!ok)return finish(verdict("failed"));
          get("https://chatgpt.com/cdn-cgi/trace",function(e,resp,data){
            var geo=!e&&status(resp)===200?find(data,/(?:^|\n)loc=([A-Za-z]{2})(?:\r?\n|$)/):"";
            finish(verdict("supported",geo));
          });
        }
        if(accepted)return finishCountry(true);
        get("https://ios.chat.openai.com/",function(e,r,data){
          if(/unsupported_country|disallowed isp/i.test(data))return finish(verdict("unsupported"));
          var good=!e&&(status(r)===200&&/openai|chatgpt/i.test(data)||
            /request is not allowed\. please try again later\./i.test(data));
          finishCountry(good);
        },{redirect:false});
      },{redirect:false});
    }else finish(verdict("failed"));
  }
  function present(v){
    if(!v)return "⚠️ 未完成";
    var labels={
      supported:["✅","可用"],available:["✅","可访问"],
      full:["✅","片源可访问"],unsupported:["⛔","受限"],
      coming:["⛔","受限"],uncertain:["⚠️","待确认"],
      failed:["⚠️","失败"]
    };
    var entry=labels[v.state]||labels.failed;
    return entry[0]+" "+entry[1]+(v.geo?" · "+v.geo:"");
  }

  function shortNode(value){
    var chars=Array.from(value);
    return chars.length<=24?value:chars.slice(0,13).join("")+"…"+chars.slice(-7).join("");
  }
  function output(){
    var ok=0;
    items.forEach(function(s){
      var v=result[s[0]];
      if(v&&["supported","available","full"].indexOf(v.state)>=0)ok++;
    });
    var lines=["节点："+shortNode(node),"",
      "可访问："+ok+" / "+items.length,""];
    items.forEach(function(s){
      lines.push(present(result[s[0]]).split(" ")[0]+" "+
        s[1]+"　"+present(result[s[0]]).slice(3));
    });
    return {title:"解锁检测",content:lines.join("\n")};
  }

  function done(){if(closed)return;closed=true;$done(output());}
  items.forEach(function(it){
    var once=false;
    try{
      test(it[0],function(v){
        if(once||closed)return;once=true;result[it[0]]=v;
        if(++completeCount===items.length)done();
      });
    }catch(e){
      if(!once&&!closed){once=true;result[it[0]]=verdict("failed");if(++completeCount===items.length)done();}
    }
  });
  setTimeout(done,22000);
})();