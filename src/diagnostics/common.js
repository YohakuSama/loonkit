/* Shared Loon adapter. Bundled locally; no runtime dependency loading. */
var LoonKit = (function () {
  "use strict";
  function argumentsValue() {
    return typeof $argument === "object" && $argument || {};
  }
  function parameters() {
    return typeof $environment === "object" && $environment && $environment.params || {};
  }
  function name(value) {
    if (typeof value !== "string") return "";
    value = value.trim();
    return !value || value.length > 200 || /[\u0000-\u001f\u007f]/.test(value) ? "" : value;
  }
  function resolveNode() {
    var env = parameters(), args = argumentsValue();
    var info = env.nodeInfo && typeof env.nodeInfo === "object" ? env.nodeInfo : {};
    var candidates = [info.name, info.tag, env.node, env.policyGroup, args.target_policy];
    var selected = "";
    for (var at = 0; at < candidates.length; at++) {
      if (typeof candidates[at] === "string" && candidates[at].trim()) {
        selected = name(candidates[at]);
        break;
      }
    }
    if (!selected) return "";
    var config = typeof $config === "object" && $config, groups = [], choices = {};
    try {
      if (config && typeof config.getConfig === "function") {
        var snapshot = JSON.parse(config.getConfig() || "{}");
        if (Array.isArray(snapshot.all_policy_groups)) groups = snapshot.all_policy_groups;
        if (snapshot.policy_select && typeof snapshot.policy_select === "object") choices = snapshot.policy_select;
      }
    } catch (error) {}
    var visited = Object.create(null);
    for (var depth = 0; depth < 16; depth++) {
      if (visited[selected] || /^(DIRECT|REJECT|REJECT-DROP|REJECT-IMG|REJECT-DICT|REJECT-ARRAY)$/i.test(selected)) return "";
      visited[selected] = true;
      var isGroup = groups.some(function (group) {
        return group === selected || group && typeof group === "object" && (group.name === selected || group.tag === selected);
      });
      var child = "";
      try {
        if (config && typeof config.getSelectedPolicy === "function") child = name(config.getSelectedPolicy(selected));
      } catch (error) {}
      if (!child) child = name(choices[selected]);
      if (child && child !== selected) { selected = child; continue; }
      if (isGroup || /^(Proxy|Auto|Fallback|ALL_Filter|Auto_Filter|Fallback_Filter)$/i.test(selected)) return "";
      return selected;
    }
    return "";
  }
  function request(method, options, callback, retry) {
    retry = retry || {};
    var attempts = 0, settled = false, budget = retry.attempts === 1 ? 1 : 2;
    function run() {
      if (settled) return;
      attempts++;
      var called = false;
      function receive(error, response, body) {
        if (called || settled) return;
        called = true;
        var code = Number(response && response.status) || 0;
        if ((error || code >= 500 && code <= 599) && attempts < budget) {
          setTimeout(run, retry.delay || 0);
          return;
        }
        settled = true;
        callback(error, response || {}, body);
      }
      try {
        if (!name(options.node)) throw new Error("A concrete request node is required");
        var client = typeof $httpClient === "object" && $httpClient;
        if (!client || typeof client[method] !== "function") throw new Error("HTTP method unavailable");
        client[method](options, receive);
      } catch (error) { receive(error, null, ""); }
    }
    run();
  }
  return {arguments: argumentsValue, parameters: parameters, resolveNode: resolveNode, request: request};
})();
