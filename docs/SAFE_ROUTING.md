# LoonKit v6.5.8 Safe Routing：符合 Loon 官方分流原则的排障方案

此配置用于判断 VPN 自动断开与复合规则订阅是否相关。**它不是已被实机确认的修复。** 仅保留在 PR 中供设备 A/B 验证，正式 `LoonKit.lcf` 与历史版本发布校验均未修改。

## 设计原则

Loon 官方文档：[匹配顺序](https://nsloon.app/docs/Rule/) · [GEOIP 与 no-resolve](https://nsloon.app/docs/Rule/ip_rule/) · [DNS 查询及缓存](https://nsloon.app/docs/DNS/)。

1. **不盲目增加国内 DIRECT 例外**。不使用静态 `.cn` 域名清单、Bilibili 域名直连清单，不把 Apple OTA / Apple 全部强制直连，更不以「避免 DNS 查询」作为添加域名直连规则的理由。
2. 排障配置移除六个复合规则订阅：`Our-RegionalCN`、`Our-AppleOTA`、`Our-Bilibili`、`Our-Microsoft`、`Our-Apple`、`Our-Paypal`。远程规则由 37 个变为 **31 个**，未增加新的订阅或补丁规则。
3. `[Rule]` 的 `GEOIP,CN,DIRECT,no-resolve` 改为 **`GEOIP,CN,DIRECT`**。原因：官方文档说明 `no-resolve` 不主动解析域名，若依赖 IP 地理位置判断尚未有目标 IP 的请求，需要允许解析。保留 `FINAL,Final` 与其他本地规则。
4. 不修改节点、策略组、通用 DNS/TUN 设置和网络诊断插件。此方案可能**不再使用**原有的 Apple / Microsoft / PayPal / Bilibili 专属策略组；这些域名如未命中其他规则，将走 GeoIP 或 Final。

**关键限制**：Loon 按「域名规则先于 IP 规则」处理请求。如果其他 31 份订阅里的域名规则先命中，即使最终解析 IP 在 CN，`GEOIP,CN,DIRECT` 也不能保证覆盖它。因此不能宣称此方案可确保所有大陆 IP 直连，也不能仅靠调整 GeoIP 在配置文件中的顺序绕开官方匹配优先级。

## Apple 与其他跨地区服务

Apple 不应视为全部在中国大陆或全部在美国。iCloud 中国大陆区与部分本地 CDN 的解析可能位于 CN，部分其他服务则在境外。不要仅凭看到代理就判断配置错误，应检查当次 DNS 解析 IP、GeoIP 地区、实际规则命中和对应节点，再决定是否需要有证据的专用规则。

Bilibili / Microsoft / PayPal 也可能因服务、接入网络和 DNS 结果而变化，不对整个品牌统一添加 DIRECT。此排障方案牺牲了六个专属策略组对特定域名的优先命中，以尽可能隔离复合规则的影响。

## DNS / ECS

- 保留已发布配置的 AliDNS DNS 设置，不未经验证就替换 DNS 服务。
- 记录出现问题时的 DNS A / AAAA / CNAME、实际连接的目标 IP、使用的 DNS 服务器、Loon 的规则命中、节点/策略以及是否命中 DNS 缓存。
- **ECS** 是由 DNS 解析器及上游共同支持的功能，不意味着所有 DNS 查询必然使用 ECS，也不能保证每次解析都返回本地最优节点。使用支持 ECS 的可信解析器或自行部署，可作为**有证据后**的定位选项，不是该修复的必要前提。
- DNS 解析仍会发生，不能把普通域名规则的使用等同于减少 DNS 查询次数。

## A/B 验证

1. 备份正式配置并记录 Loon/iOS 版本、Wi-Fi 或蜂窝、代理节点、断线时间与频率。
2. 从修复分支导入 `LoonKit.Safe.lcf`，保持**相同**网络、节点订阅、DNS、插件和测速选项。刷新远程规则。
3. 在相同条件下对比正式 v6.5.8 与 Safe 配置的 VPN 开关行为、Network Extension 退出日志和相关请求的 DNS 解析结果。
4. 如果 Safe 配置仍反复重启，再分别排查剩余订阅、网络诊断插件、测速、DNS、节点以及其他 VPN 冲突。没有实机日志不能认定复合规则是唯一根因。

在确认设备表现并完成新版发布流程前，**不要覆盖正式 `LoonKit.lcf`**。此排障配置是以临时暂停 Apple/Microsoft/PayPal/Bilibili 专用分流为代价换取隔离测试的诊断工具，不是与 v6.5.8 功能完全等价的长期替代品。
