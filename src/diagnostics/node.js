/* LoonKit · 节点信息：所选节点的配置与出口 */
(function(){
  "use strict";
  var args=LoonKit.arguments();
  var params=LoonKit.parameters();
  var info=params.nodeInfo&&typeof params.nodeInfo==="object"?params.nodeInfo:{};
  var URL="https://ipconfig.is/json";
  var completed=false;
  function val(v){
    if(typeof v!=="string"&&typeof v!=="number")return "";
    return String(v).replace(/[\u0000-\u001f\u007f]/g," ").trim().slice(0,120);
  }
  function named(v){return val(v)||"未知";}

  var selected=LoonKit.resolveNode();
  function validIP(ip){
    if(typeof ip!=="string"||ip.length<2||ip.length>45)return false;
    if(/^\d{1,3}(?:\.\d{1,3}){3}$/.test(ip))
      return ip.split(".").every(function(p){return Number(p)<=255;});
    if(!/^[0-9a-f:]+$/i.test(ip)||ip.indexOf(":")===-1)return false;
    var a=ip.split("::");
    if(a.length>2)return false;
    var pieces=ip.split(":").filter(function(p){return p.length;});
    return pieces.every(function(p){return /^[0-9a-f]{1,4}$/i.test(p);})&&
      (a.length===2?pieces.length<8:pieces.length===8);
  }
  function yes(v){return typeof v==="boolean"?(v?"检出":"未检出"):"未知";}
  function n(v){return typeof v==="number"&&isFinite(v)?v:null;}
  function done(content){
    if(completed)return;
    completed=true;
    $done({title:"节点信息",content:content});
  }
  function header(){
    var rows=["节点："+named(selected)];
    var proto=val(info.protocol)||val(info.type);
    var server=val(info.server)||val(info.address)||val(info.host);
    var port=info.port;
    if(proto)rows.push("协议："+proto);
    if(server){
      var value=server;
      if(typeof port==="number"&&port>0&&port<=65535)value+=":"+port;
      rows.push("入口："+value);
    }
    return rows;
  }
  function show(data){
    var country=val(data.country_name),code=val(data.country_code).toUpperCase();
    var place=[country+(code?" ("+code+")":""),val(data.region),val(data.city)]
      .filter(function(x){return x;}).join(" · ");
    var asn=val(data.asn);
    if(!asn&&n(data.asn_number)!==null)asn="AS"+data.asn_number;
    var lines=header().concat([
      "","【实际出口】",
      "出口 IP："+data.ip,
      "IP 版本："+(data.ip.indexOf(":")>=0?"IPv6":"IPv4"),
      "位置："+(place||"未知"),
      "运营商："+named(data.org),
      "ASN："+named(asn),
      "IP 网段："+named(data.network),
      "反向 DNS："+named(data.ptr_record),
      "时区："+named(data.timezone)
    ]);
    var lat=n(data.latitude),lon=n(data.longitude),accuracy=n(data.accuracy_radius);
    if(lat!==null&&lon!==null)
      lines.push("估算坐标："+lat.toFixed(4)+", "+lon.toFixed(4));
    if(accuracy!==null&&accuracy>0)lines.push("定位半径："+accuracy+" km");
    lines.push("","【网络识别】",
      "机房 / 云："+yes(data.is_hosting),
      "移动网络："+yes(data.is_mobile),
      "VPN / 代理："+yes(data.is_vpn),
      "Tor："+yes(data.is_tor));
    lines.push("","数据源：ipconfig.is");
    return lines;
  }
  function query(node,callback){
    LoonKit.request("get",{
      url:URL,node:node,timeout:14500,
      headers:{"Accept":"application/json","Cache-Control":"no-cache"},
      "auto-redirect":false,"auto-cookie":false,insecure:false
    },function(err,response,body){
      if(err)return callback(null,"连接失败（可能为超时或初次握手）");
      var code=Number(response&&response.status);
      if(code!==200)return callback(null,"HTTP "+(code||"异常"));
      if(typeof body!=="string"||body.length>120000)return callback(null,"响应无效");
      var data;
      try{data=JSON.parse(body);}catch(e){return callback(null,"JSON 无效");}
      if(!data||typeof data!=="object"||!validIP(data.ip))return callback(null,"没有有效出口 IP");
      callback(data,null);
    },{attempts:2,delay:350});
  }
  if(!selected){done("无法确定选中节点，请从节点菜单运行。");return;}
  query(selected,function(data,error){
    if(error){done(header().concat(["","出口信息查询失败："+error,"本次失败不等于节点不可用，请稍后复测。","数据源：ipconfig.is"]).join("\n"));return;}
    var rows=show(data);
    if(args.compare_direct!==true){done(rows.join("\n"));return;}
    query("DIRECT",function(local,localError){
      rows.push("","【直连对照】",
        "直连出口："+(localError?"查询失败":local.ip),
        "与节点出口："+(localError?"无法比较":local.ip===data.ip?"相同":"不同"));
      done(rows.join("\n"));
    });
  });
  setTimeout(function(){
    done(header().concat(["","出口信息查询超时","数据源：ipconfig.is"]).join("\n"));
  },68000);
})();
