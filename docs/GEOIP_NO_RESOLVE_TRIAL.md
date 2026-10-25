# v6.5.8 六份 GEOIP 逻辑规则的 no-resolve 诊断候选

## 已有设备实测

- v6.5.8 原始六份复合订阅全部启用时，VPN 自动断开并重连；关闭这六份后稳定。
- 曾尝试以 OR 分组减少顶层 AND 规则数 5,228 → 696，但用户复测 VPN **仍然重启**。因此该方向 **不成立**，PR #138 已关闭。
- 一次旧版 Safe 实验去掉了末尾 `GEOIP,CN,DIRECT,no-resolve` 的 `no-resolve`，用户报告 DNS 泄漏。**本候选不得修改这一行。**
- 这些观察提示可能存在带 GeoIP 的复合规则引发主动 DNS 解析/Network Extension 稳定性问题，但缺少 Loon 运行日志，不能证明根因。

## 修订内容（不同于 OR-batching）

[`LoonKit.GeoIPNoResolve.lcf`](../LoonKit.GeoIPNoResolve.lcf) **仍启用六份订阅**，共 5,228 条原始 AND/NOT 规则。六份的所有 `DOMAIN`、`DOMAIN-SUFFIX`、`IP-CIDR` 等原子匹配器都保留原顺序，**只为复合规则内部的 GEOIP 条件加 `no-resolve`**。

示例：

```ini
# 原来的 CN 分支
AND,((DOMAIN-SUFFIX,example.cn),(GEOIP,CN))
# 新的 CN 分支
AND,((DOMAIN-SUFFIX,example.cn),(GEOIP,CN,no-resolve))

# 原来的非 CN 分支
AND,((DOMAIN-SUFFIX,example.com),(NOT,((GEOIP,CN))))
# 新的非 CN 分支
AND,((DOMAIN-SUFFIX,example.com),(NOT,((GEOIP,CN,no-resolve))))
```

[Loon 官方 IP 规则](https://nsloon.app/docs/Rule/ip_rule/) 指出 `no-resolve` 不会为了域名匹配而发起 DNS 查询。官方 [逻辑规则](https://nsloon.app/docs/Rule/logic_rule/) 同时支持在条件内部使用 `GEOIP,CN,no-resolve`。

主配置里以下内容、DNS/Host/General/TUN、策略组、插件、其余 **31** 份订阅保持与正式 v6.5.8 **相同**：

```ini
GEOIP,CN,DIRECT,no-resolve
FINAL,Final
```

**重要语义差异**：原始规则可能为了 GeoIP 归属主动解析域名；新规则不主动解析未解析的域名。这会改变原版规则的 CN/非 CN 判断。CN 分支在无真实目标 IP 时可能不匹配；`NOT(GEOIP,CN,no-resolve)` 也可能因为未命中 CN 就匹配，**并不等价于已证实目标 IP 位于海外**。因此不能承诺 Apple/Microsoft/PayPal 自动按部署地区正确分流。禁止将「无 DNS 泄漏／不重启」误表述为已满足原始地区分流目标。

## 测试步骤

1. 在相同节点、Loon build、iOS 版本、Wi-Fi/蜂窝及 DNS App 开关下，备份原配置并导入 `LoonKit.GeoIPNoResolve.lcf`。
2. 刷新远程规则，确保六份资源全部成功加载；如果 Loon 报解析错误，停止本候选测试。
3. 观察 VPN 是否仍自动关闭/重连，同时检测 DNS 是否泄漏，尤其关注 Wi-Fi/移动数据和 IPv6 切换。注意 APP 内「加密 DNS 失败回退普通 DNS」开关也会影响观测。
4. 对 Apple、Microsoft、PayPal、Bilibili 的一两个具体域名，记录 DNS A/AAAA、实际请求目标 IP、GEOIP 归属、命中策略。无解析结果不等于海外。
5. 如果依旧重启，**不要继续凭空更换逻辑语法**。按 [六份原始规则的二分定位流程](https://github.com/YohakuSama/loonkit/blob/fix/loon-regional-safe-20261025/docs/SAFE_ROUTING.md) 用 Group A / Group B 及单份订阅定位；结合 Loon/iOS VPN Extension 日志查看是否为 CPU/内存或解析问题。

测试版未合并到生产版，也不修改 v6.5.8 的不可变 release 文件和哈希。所有静态回归测试的通过仅能证明预期编辑范围，不能替代真机稳定性测试。
